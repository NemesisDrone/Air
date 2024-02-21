from picasim import Plane
from low_level_pid_model import LowLevelPid


autopilot = LowLevelPid(Plane())
autopilot.run()

