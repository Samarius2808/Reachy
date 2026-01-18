"""
Menu-based Chat Controller for Reachy Mini
Simple text-based controls for conversations.

Commands:
  t / talk    - Record and send message (5 seconds)
  g / greet   - Greeting
  h / happy   - Happy expression
  s / sad     - Sad expression
  n / nod     - Nod yes
  m / no      - Shake no
  r / reset   - Reset to idle
  d / demo    - Run movement demo
  q / quit    - Exit
"""

import os
import sys
import time
import threading
from dotenv import load_dotenv

# Load environment before other imports
load_dotenv()

from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose

# Import our voice modules
from voice_interaction import (
    SpeechToText,
    TextToSpeech,
    ConversationLLM,
    RobotExpressions
)


class ChatMenu:
    """Menu-based chat controller."""

    def __init__(self):
        print("=" * 50)
        print("Reachy Mini Chat Controller")
        print("=" * 50)
        print("\nInitializing...")

        # Initialize components
        print("  Loading speech recognition (Whisper)...")
        self.stt = SpeechToText(model_size="base")

        print("  Loading text-to-speech (Azure)...")
        self.tts = TextToSpeech()

        print("  Loading LLM (Groq)...")
        self.llm = ConversationLLM()

        print("  Connecting to Reachy Mini...")
        self.robot = ReachyMini()
        self.expressions = RobotExpressions(self.robot)

        self.running = True
        print("\nReady!\n")

    def print_menu(self):
        """Print available commands."""
        print("-" * 40)
        print("COMMANDS:")
        print("  t  - Talk (record 5 sec message)")
        print("  g  - Greeting")
        print("  h  - Happy expression")
        print("  s  - Sad expression")
        print("  n  - Nod yes")
        print("  m  - Shake no")
        print("  r  - Reset to idle")
        print("  d  - Demo (movement showcase)")
        print("  q  - Quit")
        print("-" * 40)

    def talk(self, duration: float = 5.0):
        """Record speech and respond."""
        print(f"\n[Recording for {duration} seconds - speak now!]")
        self.expressions.listening_start()

        # Record
        text = self.stt.transcribe_from_mic(duration=duration)
        self.expressions.listening_stop()

        if not text.strip():
            print("You: (nothing detected)")
            self.speak("I didn't hear anything. Try again?")
            return

        print(f"You: {text}")

        # Check for goodbye
        if any(word in text.lower() for word in ["bye", "goodbye", "quit", "exit"]):
            self.speak("Goodbye! It was lovely talking with you!")
            self.expressions.happy()
            time.sleep(1)
            self.expressions.idle()
            return

        # Generate response
        print("[Thinking...]")
        self.expressions.thinking()
        response = self.llm.chat(text)
        print(f"Reachy: {response}")

        # Speak
        self.speak(response)

    def speak(self, text: str):
        """Speak with expression."""
        self.expressions.speaking_start()
        self.tts.speak(text, wait=True)
        self.expressions.speaking_stop()

    def greeting(self):
        """Friendly greeting."""
        self.expressions.greeting()
        self.speak("Hello! I'm Reachy. It's lovely to see you. How are you today?")
        self.expressions.idle()

    def happy(self):
        """Happy expression."""
        print("[Happy!]")
        self.expressions.happy()
        self.expressions.idle()

    def sad(self):
        """Sad expression."""
        print("[Sad...]")
        self.expressions.sad()
        time.sleep(1)
        self.expressions.idle()

    def nod_yes(self):
        """Nod yes."""
        print("[Nodding yes]")
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

    def shake_no(self):
        """Shake no."""
        print("[Shaking no]")
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

    def demo(self):
        """Run movement demo."""
        print("[Running demo...]")

        # Look around
        print("  Looking around...")
        self.robot.goto_target(head=create_head_pose(z=30, degrees=True), duration=0.8)
        self.robot.goto_target(head=create_head_pose(z=-30, degrees=True), duration=1.2)
        self.robot.goto_target(head=create_head_pose(), duration=0.8)

        # Antenna dance
        print("  Antenna dance...")
        for _ in range(4):
            self.robot.goto_target(antennas=[0.8, -0.8], duration=0.2)
            self.robot.goto_target(antennas=[-0.8, 0.8], duration=0.2)
        self.robot.goto_target(antennas=[0, 0], duration=0.3)

        # Happy bounce
        print("  Happy bounce...")
        for _ in range(3):
            self.robot.goto_target(
                head=create_head_pose(y=20, mm=True),
                duration=0.15
            )
            self.robot.goto_target(
                head=create_head_pose(), duration=0.15
            )

        self.expressions.idle()
        print("[Demo complete]")

    def run(self):
        """Main loop."""
        self.print_menu()

        while self.running:
            try:
                cmd = input("\n> ").strip().lower()

                if cmd in ['q', 'quit', 'exit']:
                    print("Goodbye!")
                    self.running = False

                elif cmd in ['t', 'talk']:
                    self.talk()

                elif cmd in ['g', 'greet', 'greeting']:
                    self.greeting()

                elif cmd in ['h', 'happy']:
                    self.happy()

                elif cmd in ['s', 'sad']:
                    self.sad()

                elif cmd in ['n', 'nod', 'yes']:
                    self.nod_yes()

                elif cmd in ['m', 'no', 'shake']:
                    self.shake_no()

                elif cmd in ['r', 'reset', 'idle']:
                    print("[Reset to idle]")
                    self.expressions.idle()

                elif cmd in ['d', 'demo']:
                    self.demo()

                elif cmd in ['?', 'help']:
                    self.print_menu()

                elif cmd == '':
                    pass  # Empty input, just continue

                else:
                    print(f"Unknown command: '{cmd}' (type '?' for help)")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                self.running = False
            except EOFError:
                self.running = False

        self.cleanup()

    def cleanup(self):
        """Clean up."""
        print("Cleaning up...")
        try:
            # ReachyMini may use close() or context manager
            if hasattr(self.robot, 'close'):
                self.robot.close()
            elif hasattr(self.robot, 'disconnect'):
                self.robot.disconnect()
        except Exception:
            pass
        print("Done!")


def main():
    try:
        chat = ChatMenu()
        chat.run()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. Simulation is running")
        print("  2. API keys are set in .env file")


if __name__ == "__main__":
    main()
