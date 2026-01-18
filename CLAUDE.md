# Project Context for Claude Code

## Overview

This project is developing a **companion/support robot for elderly people and nurses in care home settings** using the Pollen Robotics Reachy Mini platform.

## Hardware Status

- **Reachy Mini**: Currently waiting for hardware delivery (using simulation for now)
- **Target Configuration**: Reachy Mini Wireless
- All features should be developed and tested in simulation first, then deployed to hardware when available

## Development Environment

```bash
# Virtual environment location
~/Desktop/Coding/Reachysim/reachy_mini_venv/

# Activate environment
source reachy_mini_venv/bin/activate

# Run simulation (macOS requires mjpython)
mjpython -m reachy_mini.daemon.app.main --sim

# Run simulation with objects
mjpython -m reachy_mini.daemon.app.main --sim --scene minimal

# Dashboard
http://localhost:8000
```

## Technology Stack

- **Robot Platform**: Pollen Robotics Reachy Mini (Wireless)
- **Simulation**: MuJoCo
- **AI/ML**: Hugging Face (for models, potentially speech, vision, LLM integration)
- **SDK**: reachy-mini Python SDK
- **Development**: Python 3.12

## Use Case: Care Home Companion Robot

### Target Users
1. **Elderly residents** - companionship, reminders, entertainment, communication assistance
2. **Nurses/caregivers** - reduce workload, patient monitoring support, communication relay

### Potential Features to Prototype

#### Communication & Interaction
- [ ] Voice interaction (speech-to-text, text-to-speech)
- [ ] Emotion expression through head movements and antennas
- [ ] Active listening behaviors (nodding, head tilts)
- [ ] Conversation with LLM backend

#### Practical Assistance
- [ ] Medication reminders
- [ ] Appointment/schedule reminders
- [ ] Call nurse functionality
- [ ] Simple entertainment (jokes, stories, music)

#### Monitoring & Safety
- [ ] Check-in routines
- [ ] Mood/wellness assessment through conversation
- [ ] Alert caregivers when needed

#### Social & Emotional
- [ ] Greeting behaviors
- [ ] Personalized interactions (remember names, preferences)
- [ ] Comfort behaviors for anxious/distressed residents

## Development Approach

1. **Prototype in simulation** - Test all features in MuJoCo before hardware arrives
2. **Modular design** - Each feature as independent module for easy testing
3. **Iterative testing** - Try different approaches, see what works
4. **Hardware-ready code** - Code should work on real robot with minimal changes

## Project Structure

```
Reachysim/
├── CLAUDE.md              # This context file
├── demo.py                # Basic movement demo
├── reachy_mini_venv/      # Python virtual environment
├── installation.md        # SDK installation guide
├── simulation_setup.md    # Simulation setup guide
└── [feature modules]      # To be developed
```

## Notes for Claude Code

- Help improve development efficiency by writing, testing, and iterating on features
- Always test in simulation before suggesting hardware deployment
- Focus on practical, care-home-appropriate interactions
- Consider accessibility (elderly users may have hearing/vision limitations)
- Keep interactions gentle, patient, and reassuring in tone
- Code should be well-documented for future reference

## Resources

- [Reachy Mini SDK Docs](https://github.com/pollen-robotics/reachy_mini)
- [Hugging Face](https://huggingface.co/)
- [MuJoCo](https://mujoco.org/)
