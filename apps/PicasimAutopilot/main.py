from picasim import Plane
from low_level_pid_model import LowLevelPid
from simple_auto_pilot_wing_level import SimpleAutoPilotWingLevel


# autopilot = LowLevelPid(Plane())
# autopilot.run()

autopilot = SimpleAutoPilotWingLevel(Plane())
autopilot.run()

