"""Reachy Mini Demo Script - Play with the robot!"""

import time
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose


def main():
    print("Connecting to Reachy Mini simulation...")

    with ReachyMini() as mini:
        print("Connected! Starting demo...\n")

        # 1. Look around
        print("1. Looking around...")
        mini.goto_target(head=create_head_pose(z=30, degrees=True), duration=0.8)
        mini.goto_target(head=create_head_pose(z=-30, degrees=True), duration=1.2)
        mini.goto_target(head=create_head_pose(z=0, degrees=True), duration=0.8)

        # 2. Nod yes
        print("2. Nodding yes...")
        for _ in range(3):
            mini.goto_target(head=create_head_pose(y=15, mm=True), duration=0.3)
            mini.goto_target(head=create_head_pose(y=-10, mm=True), duration=0.3)
        mini.goto_target(head=create_head_pose(), duration=0.3)

        # 3. Shake no
        print("3. Shaking no...")
        for _ in range(3):
            mini.goto_target(head=create_head_pose(z=20, degrees=True), duration=0.2)
            mini.goto_target(head=create_head_pose(z=-20, degrees=True), duration=0.2)
        mini.goto_target(head=create_head_pose(), duration=0.3)

        # 4. Tilt head (curious)
        print("4. Looking curious...")
        mini.goto_target(head=create_head_pose(roll=25, degrees=True), duration=0.5)
        time.sleep(0.5)
        mini.goto_target(head=create_head_pose(roll=-25, degrees=True), duration=0.7)
        time.sleep(0.5)
        mini.goto_target(head=create_head_pose(), duration=0.5)

        # 5. Antenna dance
        print("5. Antenna dance...")
        for _ in range(4):
            mini.goto_target(antennas=[0.8, -0.8], duration=0.2)
            mini.goto_target(antennas=[-0.8, 0.8], duration=0.2)
        mini.goto_target(antennas=[0, 0], duration=0.3)

        # 6. Happy bounce
        print("6. Happy bounce...")
        for _ in range(3):
            mini.goto_target(head=create_head_pose(y=20, mm=True), duration=0.15)
            mini.goto_target(head=create_head_pose(y=0, mm=True), duration=0.15)

        # 7. Combination move
        print("7. Showing off...")
        mini.goto_target(
            head=create_head_pose(z=20, roll=15, degrees=True),
            antennas=[0.5, -0.3],
            duration=0.8
        )
        time.sleep(0.3)
        mini.goto_target(
            head=create_head_pose(z=-20, roll=-15, degrees=True),
            antennas=[-0.3, 0.5],
            duration=0.8
        )
        time.sleep(0.3)

        # Reset to neutral
        print("8. Returning to rest position...")
        mini.goto_target(
            head=create_head_pose(),
            antennas=[0, 0],
            duration=1.0
        )

        print("\nDemo complete!")


if __name__ == "__main__":
    main()
