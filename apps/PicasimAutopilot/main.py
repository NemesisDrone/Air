from picasim import Plane
from low_level_pid_model import LowLevelPid
from simple_auto_pilot_wing_level import SimpleAutoPilotWingLevel
from test_model import TestAutoPilot


# autopilot = LowLevelPid(Plane())
# autopilot.run()

# autopilot = SimpleAutoPilotWingLevel(Plane())
# autopilot.run()

autopilot = TestAutoPilot(Plane())
autopilot.run()
