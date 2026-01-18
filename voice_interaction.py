"""
Voice Interaction Module for Reachy Mini
- Speech-to-Text: OpenAI Whisper (local)
- Text-to-Speech: Microsoft Azure TTS
- LLM: Groq Llama 3.3 70B
"""

import os
import time
import threading
import tempfile
import wave
from typing import Optional, Callable
from dotenv import load_dotenv

import whisper
import azure.cognitiveservices.speech as speechsdk
from groq import Groq

from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose

# Load environment variables
load_dotenv()


class SpeechToText:
    """Local Whisper-based speech recognition."""

    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper model.

        Args:
            model_size: One of 'tiny', 'base', 'small', 'medium', 'large'
                       Smaller = faster, larger = more accurate
        """
        print(f"Loading Whisper model ({model_size})...")
        self.model = whisper.load_model(model_size)
        print("Whisper model loaded.")

    def transcribe(self, audio_file: str) -> str:
        """Transcribe audio file to text."""
        result = self.model.transcribe(audio_file)
        return result["text"].strip()

    def transcribe_from_mic(self, duration: float = 5.0) -> str:
        """Record from microphone and transcribe."""
        import pyaudio

        # Recording parameters
        chunk = 1024
        format = pyaudio.paInt16
        channels = 1
        rate = 16000

        p = pyaudio.PyAudio()
        stream = p.open(
            format=format,
            channels=channels,
            rate=rate,
            input=True,
            frames_per_buffer=chunk
        )

        print(f"Recording for {duration} seconds...")
        frames = []
        for _ in range(int(rate / chunk * duration)):
            data = stream.read(chunk)
            frames.append(data)

        print("Recording finished.")
        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wf = wave.open(temp_path, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(format))
            wf.setframerate(rate)
            wf.writeframes(b''.join(frames))
            wf.close()

        # Transcribe
        text = self.transcribe(temp_path)
        os.unlink(temp_path)
        return text


class TextToSpeech:
    """Azure TTS for natural speech synthesis."""

    def __init__(
        self,
        speech_key: Optional[str] = None,
        speech_region: Optional[str] = None,
        voice_name: str = "en-US-JennyNeural"
    ):
        """
        Initialize Azure TTS.

        Args:
            speech_key: Azure Speech API key (or set AZURE_SPEECH_KEY env var)
            speech_region: Azure region (or set AZURE_SPEECH_REGION env var)
            voice_name: Voice to use (e.g., 'en-US-JennyNeural', 'en-GB-SoniaNeural')
        """
        self.speech_key = speech_key or os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = speech_region or os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.voice_name = voice_name

        if not self.speech_key:
            raise ValueError("Azure Speech key required. Set AZURE_SPEECH_KEY env var.")

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )
        self.speech_config.speech_synthesis_voice_name = self.voice_name

    def speak(self, text: str, wait: bool = True) -> None:
        """Synthesize and play speech."""
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

        if wait:
            result = synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                print(f"TTS canceled: {cancellation.reason}")
                if cancellation.error_details:
                    print(f"Error: {cancellation.error_details}")
        else:
            synthesizer.speak_text_async(text)

    def speak_ssml(self, ssml: str) -> None:
        """Speak using SSML for more control over prosody."""
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        synthesizer.speak_ssml_async(ssml).get()


class ConversationLLM:
    """Groq-based LLM for generating responses."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile"
    ):
        """
        Initialize Groq LLM.

        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
            model: Model to use
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY env var.")

        self.client = Groq(api_key=self.api_key)
        self.model = model
        self.conversation_history = []

        # System prompt for care home companion
        self.system_prompt = """You are Reachy, a friendly companion robot in a care home.
You interact with elderly residents and help nursing staff.

Your personality:
- Warm, patient, and caring
- Speak clearly and not too fast
- Use simple, easy-to-understand language
- Be encouraging and positive
- Show genuine interest in the person you're talking to

Keep responses concise (1-3 sentences) unless asked for more detail.
If someone seems confused or distressed, be extra gentle and reassuring.
You can tell jokes, share interesting facts, or just have a friendly chat."""

    def chat(self, user_message: str) -> str:
        """Generate a response to the user's message."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history[-10:]  # Keep last 10 exchanges

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )

        assistant_message = response.choices[0].message.content
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    def reset_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []


class RobotExpressions:
    """Expressive movements for Reachy Mini during conversation."""

    def __init__(self, robot: ReachyMini):
        self.robot = robot
        self._speaking = False
        self._listening = False

    def idle(self):
        """Return to neutral position."""
        self.robot.goto_target(
            head=create_head_pose(),
            antennas=[0, 0],
            duration=0.5
        )

    def listening_start(self):
        """Show attentive listening pose."""
        self._listening = True
        # Slight head tilt and raised antennas
        self.robot.goto_target(
            head=create_head_pose(roll=8, degrees=True),
            antennas=[0.3, 0.3],
            duration=0.4
        )

    def listening_nod(self):
        """Occasional nod while listening."""
        if self._listening:
            self.robot.goto_target(
                head=create_head_pose(y=10, roll=8, mm=True, degrees=True),
                duration=0.2
            )
            self.robot.goto_target(
                head=create_head_pose(roll=8, degrees=True),
                duration=0.2
            )

    def listening_stop(self):
        """End listening pose."""
        self._listening = False
        self.idle()

    def thinking(self):
        """Show thinking expression."""
        self.robot.goto_target(
            head=create_head_pose(z=15, roll=-10, degrees=True),
            antennas=[0.2, -0.2],
            duration=0.5
        )
        time.sleep(0.3)

    def speaking_start(self):
        """Begin speaking animation in background."""
        self._speaking = True
        threading.Thread(target=self._speaking_animation, daemon=True).start()

    def _speaking_animation(self):
        """Subtle movements while speaking."""
        while self._speaking:
            # Small head movements
            self.robot.goto_target(
                head=create_head_pose(z=3, degrees=True),
                duration=0.3
            )
            if not self._speaking:
                break
            self.robot.goto_target(
                head=create_head_pose(z=-3, degrees=True),
                duration=0.3
            )
            if not self._speaking:
                break

    def speaking_stop(self):
        """Stop speaking animation."""
        self._speaking = False
        time.sleep(0.1)
        self.idle()

    def happy(self):
        """Express happiness."""
        for _ in range(2):
            self.robot.goto_target(
                head=create_head_pose(y=15, mm=True),
                antennas=[0.5, 0.5],
                duration=0.2
            )
            self.robot.goto_target(
                head=create_head_pose(),
                antennas=[0.2, 0.2],
                duration=0.2
            )

    def sad(self):
        """Express sadness/empathy."""
        self.robot.goto_target(
            head=create_head_pose(y=-10, roll=5, mm=True, degrees=True),
            antennas=[-0.3, -0.3],
            duration=0.8
        )

    def greeting(self):
        """Friendly greeting gesture."""
        self.robot.goto_target(
            head=create_head_pose(y=10, mm=True),
            antennas=[0.6, 0.6],
            duration=0.4
        )
        time.sleep(0.3)
        self.robot.goto_target(
            antennas=[0.3, 0.3],
            duration=0.3
        )


class VoiceInteraction:
    """Main voice interaction system combining all components."""

    def __init__(
        self,
        robot: Optional[ReachyMini] = None,
        whisper_model: str = "base",
        azure_voice: str = "en-US-JennyNeural"
    ):
        """
        Initialize the complete voice interaction system.

        Args:
            robot: ReachyMini instance (creates one if not provided)
            whisper_model: Whisper model size
            azure_voice: Azure TTS voice name
        """
        print("Initializing Voice Interaction System...")

        # Initialize components
        self.stt = SpeechToText(model_size=whisper_model)
        self.tts = TextToSpeech(voice_name=azure_voice)
        self.llm = ConversationLLM()

        # Robot connection
        self._own_robot = robot is None
        self.robot = robot or ReachyMini()
        self.expressions = RobotExpressions(self.robot)

        print("Voice Interaction System ready!")

    def greet(self):
        """Perform initial greeting."""
        self.expressions.greeting()
        greeting = "Hello! I'm Reachy. It's lovely to meet you. How are you today?"
        self.speak(greeting)

    def listen(self, duration: float = 5.0) -> str:
        """Listen for user speech."""
        self.expressions.listening_start()
        text = self.stt.transcribe_from_mic(duration=duration)
        self.expressions.listening_stop()
        return text

    def think_and_respond(self, user_input: str) -> str:
        """Generate and return a response."""
        self.expressions.thinking()
        response = self.llm.chat(user_input)
        return response

    def speak(self, text: str):
        """Speak text with expressions."""
        self.expressions.speaking_start()
        self.tts.speak(text, wait=True)
        self.expressions.speaking_stop()

    def conversation_turn(self, listen_duration: float = 5.0) -> tuple[str, str]:
        """
        Complete one turn of conversation.

        Returns:
            Tuple of (user_input, robot_response)
        """
        # Listen
        print("\nListening...")
        user_input = self.listen(duration=listen_duration)
        print(f"You said: {user_input}")

        if not user_input.strip():
            response = "I didn't quite catch that. Could you say that again?"
            self.speak(response)
            return "", response

        # Think and respond
        print("Thinking...")
        response = self.think_and_respond(user_input)
        print(f"Reachy: {response}")

        # Speak
        self.speak(response)

        return user_input, response

    def run_conversation(self, num_turns: int = 5):
        """Run a multi-turn conversation."""
        self.greet()

        for i in range(num_turns):
            print(f"\n--- Turn {i + 1}/{num_turns} ---")
            user_input, _ = self.conversation_turn()

            # Check for goodbye
            if any(word in user_input.lower() for word in ["bye", "goodbye", "see you"]):
                self.speak("Goodbye! It was lovely talking with you. Take care!")
                self.expressions.happy()
                break

        self.expressions.idle()

    def close(self):
        """Clean up resources."""
        if self._own_robot:
            try:
                if hasattr(self.robot, 'close'):
                    self.robot.close()
            except Exception:
                pass


def main():
    """Run a demo conversation."""
    print("=" * 50)
    print("Reachy Mini Voice Interaction Demo")
    print("=" * 50)

    try:
        with ReachyMini() as robot:
            voice = VoiceInteraction(robot=robot)
            voice.run_conversation(num_turns=5)
    except KeyboardInterrupt:
        print("\nConversation ended by user.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have set up your API keys in .env file:")
        print("  GROQ_API_KEY=your_key")
        print("  AZURE_SPEECH_KEY=your_key")
        print("  AZURE_SPEECH_REGION=your_region")


if __name__ == "__main__":
    main()
