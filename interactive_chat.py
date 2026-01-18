"""
Interactive Chat Controller for Reachy Mini
Push-to-talk and hotkey controls for conversations.

Controls:
  SPACE  - Hold to talk (push-to-talk)
  ENTER  - Toggle recording on/off
  G      - Greeting
  H      - Happy expression
  S      - Sad expression
  T      - Thinking expression
  N      - Nod yes
  M      - Shake no (M for "mmm-mmm")
  R      - Reset to idle
  Q      - Quit
"""

import os
import sys
import time
import threading
import tempfile
import wave
from typing import Optional
from dotenv import load_dotenv

# Load environment before other imports
load_dotenv()

import pyaudio
from pynput import keyboard

from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose

# Import our voice modules
from voice_interaction import (
    SpeechToText,
    TextToSpeech,
    ConversationLLM,
    RobotExpressions
)


class AudioRecorder:
    """Handle audio recording with start/stop control."""

    def __init__(self):
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.frames = []
        self.is_recording = False
        self.pyaudio = pyaudio.PyAudio()
        self.stream = None

    def start_recording(self):
        """Start recording audio."""
        if self.is_recording:
            return

        self.frames = []
        self.is_recording = True
        self.stream = self.pyaudio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        # Record in background thread
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()

    def _record_loop(self):
        """Recording loop running in background."""
        while self.is_recording and self.stream:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
            except Exception:
                break

    def stop_recording(self) -> Optional[str]:
        """Stop recording and return path to audio file."""
        if not self.is_recording:
            return None

        self.is_recording = False
        time.sleep(0.1)  # Let recording thread finish

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        if not self.frames:
            return None

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wf = wave.open(temp_path, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.pyaudio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
            wf.close()

        return temp_path

    def cleanup(self):
        """Clean up resources."""
        self.is_recording = False
        if self.stream:
            self.stream.close()
        self.pyaudio.terminate()


class InteractiveChat:
    """Interactive chat controller with hotkeys."""

    def __init__(self):
        print("Initializing Interactive Chat...")
        print("Loading components...")

        # Initialize components
        self.stt = SpeechToText(model_size="base")
        self.tts = TextToSpeech()
        self.llm = ConversationLLM()
        self.recorder = AudioRecorder()

        # Robot connection
        print("Connecting to Reachy Mini...")
        self.robot = ReachyMini()
        self.expressions = RobotExpressions(self.robot)

        # State
        self.is_recording = False
        self.is_processing = False
        self.running = True

        print("\nReady!")
        self._print_controls()

    def _print_controls(self):
        """Print control instructions."""
        print("\n" + "=" * 50)
        print("CONTROLS")
        print("=" * 50)
        print("  SPACE  - Hold to talk (push-to-talk)")
        print("  ENTER  - Toggle recording on/off")
        print("  G      - Greeting")
        print("  H      - Happy expression")
        print("  S      - Sad expression")
        print("  T      - Thinking expression")
        print("  N      - Nod yes")
        print("  M      - Shake no")
        print("  R      - Reset to idle")
        print("  Q      - Quit")
        print("=" * 50)
        print("\nPress SPACE and speak, or use hotkeys...\n")

    def _on_press(self, key):
        """Handle key press events."""
        try:
            # Check for character keys
            if hasattr(key, 'char') and key.char:
                char = key.char.lower()

                if char == 'q':
                    print("\nQuitting...")
                    self.running = False
                    return False  # Stop listener

                elif char == 'g':
                    print("[Greeting]")
                    threading.Thread(target=self._do_greeting, daemon=True).start()

                elif char == 'h':
                    print("[Happy]")
                    threading.Thread(target=self.expressions.happy, daemon=True).start()

                elif char == 's':
                    print("[Sad]")
                    threading.Thread(target=self.expressions.sad, daemon=True).start()

                elif char == 't':
                    print("[Thinking]")
                    threading.Thread(target=self.expressions.thinking, daemon=True).start()

                elif char == 'n':
                    print("[Nodding yes]")
                    threading.Thread(target=self._nod_yes, daemon=True).start()

                elif char == 'm':
                    print("[Shaking no]")
                    threading.Thread(target=self._shake_no, daemon=True).start()

                elif char == 'r':
                    print("[Reset to idle]")
                    threading.Thread(target=self.expressions.idle, daemon=True).start()

            # Check for special keys
            elif key == keyboard.Key.space:
                if not self.is_recording and not self.is_processing:
                    self._start_recording()

            elif key == keyboard.Key.enter:
                if self.is_recording:
                    self._stop_and_process()
                elif not self.is_processing:
                    self._start_recording()

        except Exception as e:
            print(f"Key error: {e}")

    def _on_release(self, key):
        """Handle key release events."""
        try:
            if key == keyboard.Key.space:
                if self.is_recording:
                    self._stop_and_process()
        except Exception:
            pass

    def _start_recording(self):
        """Start recording user speech."""
        if self.is_recording or self.is_processing:
            return

        self.is_recording = True
        print("\n[Recording... speak now]")
        self.expressions.listening_start()
        self.recorder.start_recording()

    def _stop_and_process(self):
        """Stop recording and process the speech."""
        if not self.is_recording:
            return

        self.is_recording = False
        self.is_processing = True
        print("[Processing...]")

        # Stop recording
        audio_path = self.recorder.stop_recording()
        self.expressions.listening_stop()

        if audio_path:
            # Process in background
            threading.Thread(
                target=self._process_audio,
                args=(audio_path,),
                daemon=True
            ).start()
        else:
            print("[No audio recorded]")
            self.is_processing = False

    def _process_audio(self, audio_path: str):
        """Process recorded audio and respond."""
        try:
            # Transcribe
            text = self.stt.transcribe(audio_path)
            os.unlink(audio_path)  # Clean up temp file

            if not text.strip():
                print("You: (silence)")
                self.tts.speak("I didn't catch that. Could you try again?")
                self.is_processing = False
                return

            print(f"You: {text}")

            # Check for goodbye
            if any(word in text.lower() for word in ["bye", "goodbye", "see you", "quit", "exit"]):
                print("Reachy: Goodbye! Take care!")
                self.expressions.happy()
                self.tts.speak("Goodbye! It was lovely talking with you. Take care!")
                self.expressions.idle()
                self.is_processing = False
                return

            # Think and respond
            self.expressions.thinking()
            response = self.llm.chat(text)
            print(f"Reachy: {response}")

            # Speak with expression
            self.expressions.speaking_start()
            self.tts.speak(response, wait=True)
            self.expressions.speaking_stop()

        except Exception as e:
            print(f"Error processing: {e}")

        finally:
            self.is_processing = False

    def _do_greeting(self):
        """Perform greeting."""
        self.expressions.greeting()
        self.tts.speak("Hello! I'm Reachy. How can I help you today?")
        self.expressions.idle()

    def _nod_yes(self):
        """Nod yes gesture."""
        for _ in range(3):
            self.robot.goto_target(
                head=create_head_pose(y=15, mm=True),
                duration=0.25
            )
            self.robot.goto_target(
                head=create_head_pose(y=-10, mm=True),
                duration=0.25
            )
        self.expressions.idle()

    def _shake_no(self):
        """Shake no gesture."""
        for _ in range(3):
            self.robot.goto_target(
                head=create_head_pose(z=20, degrees=True),
                duration=0.2
            )
            self.robot.goto_target(
                head=create_head_pose(z=-20, degrees=True),
                duration=0.2
            )
        self.expressions.idle()

    def run(self):
        """Run the interactive chat loop."""
        # Start keyboard listener
        with keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        ) as listener:
            # Keep running until quit
            while self.running:
                time.sleep(0.1)

        self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        print("\nCleaning up...")
        self.recorder.cleanup()
        self.robot.disconnect()
        print("Done!")


def main():
    print("=" * 50)
    print("Reachy Mini Interactive Chat")
    print("=" * 50)

    try:
        chat = InteractiveChat()
        chat.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. Simulation is running (mjpython -m reachy_mini.daemon.app.main --sim)")
        print("  2. API keys are set in .env file")


if __name__ == "__main__":
    main()
