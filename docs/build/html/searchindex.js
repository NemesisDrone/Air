Search.setIndex({"docnames": ["docs/components", "docs/components/manager", "docs/components/nemesis_utilities", "docs/components/nemesis_utilities/component", "docs/components/nemesis_utilities/ipc", "docs/getting_started", "docs/ipc_routes", "index"], "filenames": ["docs/components.rst", "docs/components/manager.rst", "docs/components/nemesis_utilities.rst", "docs/components/nemesis_utilities/component.rst", "docs/components/nemesis_utilities/ipc.rst", "docs/getting_started.rst", "docs/ipc_routes.rst", "index.rst"], "titles": ["Components", "The Manager", "Nemesis utilities", "Component", "IPC", "Getting Started", "IPC Routes", "Nemesis Air Documentation"], "terms": {"project": [0, 1], "follow": [0, 1, 2, 5], "modular": 0, "approach": 0, "The": [0, 2, 3, 4, 5, 6], "i": [0, 1, 2, 3, 4, 5, 6], "divid": 0, "sever": 0, "each": [0, 2], "one": [0, 3, 4, 5], "its": [0, 2, 3, 6], "own": [0, 2, 3, 4], "purpos": [0, 2, 6], "tabl": 0, "show": [0, 5], "nemesis_util": [0, 2, 3, 4, 6], "expos": [0, 2], "util": [0, 3, 4, 6], "librari": [0, 2], "all": [0, 2, 3, 4, 5, 6], "reusabl": [0, 2], "code": [0, 2, 5], "manag": [0, 3, 5, 6], "orchestr": 0, "execut": [0, 5], "nemesi": [1, 5], "air": [1, 5], "base": [1, 3, 4, 5], "architectur": 1, "everi": [1, 6], "part": 1, "run": [1, 2, 3], "object": [1, 3, 4], "A": [1, 3, 4], "initi": 1, "start": [1, 3, 4, 6, 7], "stop": [1, 3, 4, 6], "These": [1, 5], "state": [1, 3], "chang": [1, 5], "ar": [1, 3, 5, 6], "To": [1, 2, 5], "pleas": [1, 5], "see": [1, 3, 4, 5, 6], "thi": [1, 3, 4, 6], "guid": [1, 5, 7], "come": 1, "soon": 1, "compon": [2, 4, 5, 6], "from": [2, 3, 4, 6], "your": [2, 4, 5], "you": [2, 4, 5, 7], "can": [2, 4, 5, 6, 7], "import": [2, 3, 5], "them": 2, "module_nam": 2, "automat": [2, 4, 5], "instal": 2, "therefor": 2, "avail": [2, 5], "ase": 2, "long": 2, "docker": 2, "contain": [2, 4, 5], "ipc": [2, 3], "ipcnod": [2, 3, 4, 6], "class": [2, 3, 4, 6], "commun": [2, 4], "togeth": 2, "creat": [2, 4, 5], "microservic": [2, 3], "process": [2, 3, 5], "modul": [3, 4, 5, 7], "implement": [3, 4], "repres": 3, "handl": 3, "meant": [3, 4], "subclass": 3, "should": [3, 4, 5], "overrid": 3, "method": [3, 4, 6], "name": [3, 4, 5, 6], "attribut": 3, "testcompon": 3, "test": [3, 4, 5, 6], "def": [3, 4], "__init__": [3, 4], "self": [3, 4], "super": 3, "veri": 3, "do": 3, "forget": [3, 4], "line": 3, "some": [3, 5], "init": 3, "stuff": 3, "here": 3, "log": [3, 4, 5], "time": [3, 4, 6], "sleep": 3, "1": [3, 5, 6], "2": 3, "output": [3, 4], "without": [3, 4, 5], "debug": [3, 4, 5], "15": [3, 4], "10": [3, 4], "2023": [3, 4], "12": 3, "35": 3, "56": 3, "info": [3, 4], "59": 3, "src": [3, 4, 6], "enumer": 3, "possibl": 3, "up": [3, 5], "shut": 3, "down": 3, "singl": [3, 4, 6], "us": [3, 4, 6], "directli": [3, 4, 5], "rather": 3, "current": 3, "pick": [3, 4], "overridden": 3, "never": [3, 6], "send": [3, 4, 6], "messag": [3, 4, 6], "itself": 3, "loopback": [3, 4], "paramet": [3, 4], "caus": 3, "deadlock": 3, "str": [3, 4], "level": [3, 4, 6], "extra_rout": [3, 4], "none": [3, 4], "stdout": [3, 4, 6], "system": [3, 4, 6], "component_nam": 3, "rout": [3, 4], "loglevel": [3, 4], "default": [3, 4, 5], "an": [3, 4, 5], "addit": [3, 4, 6], "extra": [3, 4], "append": [3, 4], "exampl": [3, 4, 5], "give": [3, 4, 6], "b": [3, 4], "c": [3, 4, 5], "sent": [3, 4, 6], "label": [3, 4, 6], "result": [3, 4], "data": [3, 4, 6], "bool": [3, 4], "fals": [3, 4, 6], "_nolog": [3, 4], "block": [3, 4], "wait": [3, 4, 5], "respons": [3, 4], "match": [3, 4], "regex": [3, 4], "given": [3, 4], "decor": [3, 4], "dict": [3, 4], "pass": [3, 4], "callback": [3, 4], "function": [3, 4], "must": [3, 4], "pickl": [3, 4], "serializ": [3, 4], "If": [3, 4, 5, 6], "true": [3, 4, 6], "node": [3, 4, 6], "abl": [3, 4], "receiv": [3, 4], "send_block": [3, 4], "timeout": [3, 4], "float": [3, 4], "5": [3, 4], "0": [3, 4], "rais": [3, 4], "except": [3, 4], "ha": [3, 4], "onli": [3, 4, 5], "second": [3, 4], "return": [3, 4], "reach": [3, 4], "wa": [3, 4, 5], "error": [3, 4, 5], "occur": [3, 4], "valu": [3, 4, 5, 6], "serial": [3, 4], "alwai": [3, 4], "correctli": [3, 4], "check": [3, 4, 5], "catch": [3, 4], "ani": [3, 4, 6], "ipc_id": [3, 4], "id": [3, 4, 5], "r": [3, 4, 5], "redi": [3, 4, 6], "strictredi": [3, 4], "client": [3, 4], "pubsub": [3, 4, 6], "subscrib": [3, 4, 6], "flag": [3, 4, 5], "listen": [3, 4], "thread": [3, 4], "while": [3, 4], "continu": [3, 4], "new": [3, 4], "map": [3, 4], "blocking_respons": [3, 4], "blocking_response_rout": [3, 4], "semaphor": [3, 4], "field": [3, 4, 5], "list": [3, 4, 5], "simpl": 4, "allow": [4, 5], "other": [4, 5], "call": 4, "when": [4, 5, 6], "channel": [4, 6], "provid": 4, "pingpongnod": 4, "regist": 4, "ping": 4, "payload": 4, "pong": 4, "sinc": 4, "want": [4, 5], "set": [4, 5], "extra_messag": 4, "hello": 4, "world": 4, "access": 4, "return_pi": 4, "back": 4, "sender": 4, "3": [4, 5], "14159265359": 4, "n": [4, 6], "same": [4, 5], "don": 4, "t": 4, "13": 4, "06": 4, "51": 4, "For": [4, 5], "more": [4, 6], "advanc": 4, "document": 4, "bellow": 4, "arg": 4, "have": [4, 5], "also": [4, 5, 6], "work": [4, 6], "multipl": 4, "until": 4, "befor": 4, "With": 4, "mode": [4, 5, 6], "json": 4, "otherwis": 4, "warn": [4, 6], "print": 4, "Be": 4, "sure": 4, "onc": 4, "first": 4, "side": 4, "critic": 4, "enum": 4, "host": 4, "port": 4, "6379": 4, "db": [4, 6], "kwarg": 4, "just": [4, 5], "need": [4, 5], "inherit": 4, "random": 4, "uuid": 4, "gener": [4, 5], "server": [4, 5], "hostnam": 4, "int": 4, "ensur": 4, "servic": 4, "let": 5, "": [5, 6], "repositori": 5, "page": [5, 6, 7], "through": 5, "workflow": 5, "On": 5, "both": 5, "window": 5, "linux": 5, "softwar": 5, "desktop": 5, "python3": 5, "doc": 5, "python": 5, "depend": [5, 6], "pip": 5, "txt": 5, "refer": [5, 6], "section": 5, "dockerfil": 5, "build": 5, "isol": 5, "environ": 5, "file": 5, "yml": 5, "develop": 5, "reflect": 5, "rebuild": 5, "prod": 5, "product": 5, "root": 5, "command": 5, "directori": 5, "dev": 5, "specifi": 5, "what": 5, "f": 5, "entri": 5, "point": 5, "profil": 5, "hardcod": 5, "prepend": 5, "profile_nam": 5, "d": 5, "step": 5, "explain": 5, "how": 5, "pycharm": 5, "insid": 5, "raspberri": 5, "pi": 5, "go": 5, "click": 5, "add": 5, "detect": [5, 6], "button": 5, "select": 5, "plu": 5, "env": 5, "variabl": 5, "fill": 5, "avoid": 5, "conflict": 5, "two": 5, "differ": 5, "classic": 5, "next": 5, "bottom": 5, "right": 5, "corner": 5, "easili": 5, "switch": 5, "between": 5, "There": 5, "often": 5, "issu": 5, "lead": 5, "symbol": 5, "being": 5, "load": 5, "statement": 5, "re": 5, "menu": 5, "script": 5, "manual": 5, "learn": 5, "tutori": 5, "memori": 6, "mechan": 6, "good": 6, "abstract": 6, "detail": 6, "about": 6, "charact": 6, "than": 6, "letter": 6, "break": 6, "describ": 6, "structur": 6, "timestamp": 6, "complet": 6, "filter": 6, "termin": 6, "_stdoverrid": 6, "stderr": 6, "ask": 6, "alreadi": 6, "noth": 6, "happen": 6, "restart": 6, "again": 6, "stop_al": 6, "restart_al": 6, "store": 6, "kei": 6, "updat": 6, "full": 6, "raw": [], "roll": 6, "180": 6, "pitch": 6, "yaw": 6, "gyrorol": 6, "radian": 6, "gyropitch": 6, "gyroyaw": 6, "accelx": 6, "g": 6, "acc": 6, "accelz": 6, "compassx": 6, "ut": 6, "micro": 6, "tesla": 6, "compassi": 6, "compassz": 6, "pressur": 6, "millibar": 6, "broken": 6, "temperatur": 6, "celciu": 6, "humid": 6, "percentag": 6, "welcom": 7, "read": [6, 7], "get": 7, "index": 7, "search": 7, "br": [], "angl": 6, "gyroscop": 6, "x": 6, "acceleromet": 6, "y": 6, "z": 6, "compass": 6, "accur": 6, "inform": 6, "laser": 6, "distanc": 6, "measur": 6, "aliv": 6, "valid": 6, "sim7600": 6, "gnss": 6, "fixmod": 6, "fix": 6, "useless": 6, "gpssat": 6, "number": 6, "gp": 6, "satellit": 6, "glosat": 6, "glonass": 6, "beisat": 6, "beidou": 6, "lat": 6, "latitud": 6, "format": 6, "degre": 6, "minut": 6, "latind": 6, "indic": 6, "multipli": 6, "lon": 6, "longitud": 6, "lonind": 6, "e": 6, "w": 6, "date": 6, "ddmmyi": 6, "hhmmss": 6, "alt": 6, "altitud": 6, "meter": 6, "speed": 6, "km": 6, "h": 6, "cours": 6, "pdop": 6, "hdop": 6, "vdop": 6}, "objects": {"src.nemesis_utilities.utilities": [[3, 0, 0, "-", "component"], [4, 0, 0, "-", "ipc"]], "src.nemesis_utilities.utilities.component": [[3, 1, 1, "", "Component"], [3, 1, 1, "", "State"]], "src.nemesis_utilities.utilities.component.Component": [[3, 2, 1, "", "NAME"], [3, 2, 1, "", "blocking_responses"], [3, 2, 1, "", "ipc_id"], [3, 2, 1, "", "listening"], [3, 3, 1, "", "log"], [3, 2, 1, "", "pubsub"], [3, 2, 1, "", "r"], [3, 2, 1, "", "regexes"], [3, 3, 1, "", "send"], [3, 3, 1, "", "send_blocking"], [3, 3, 1, "", "start"], [3, 2, 1, "", "state"], [3, 3, 1, "", "stop"], [3, 2, 1, "", "subscribed"]], "src.nemesis_utilities.utilities.component.State": [[3, 2, 1, "", "STARTED"], [3, 2, 1, "", "STARTING"], [3, 2, 1, "", "STOPPED"], [3, 2, 1, "", "STOPPING"]], "src.nemesis_utilities.utilities.ipc": [[4, 1, 1, "", "IpcNode"], [4, 1, 1, "", "LogLevels"], [4, 4, 1, "", "route"]], "src.nemesis_utilities.utilities.ipc.IpcNode": [[4, 3, 1, "", "__init__"], [4, 2, 1, "", "blocking_responses"], [4, 2, 1, "", "ipc_id"], [4, 2, 1, "", "listening"], [4, 3, 1, "", "log"], [4, 2, 1, "", "pubsub"], [4, 2, 1, "", "r"], [4, 2, 1, "", "regexes"], [4, 3, 1, "", "send"], [4, 3, 1, "", "send_blocking"], [4, 3, 1, "", "start"], [4, 3, 1, "", "stop"], [4, 2, 1, "", "subscribed"]], "src.nemesis_utilities.utilities.ipc.LogLevels": [[4, 2, 1, "", "CRITICAL"], [4, 2, 1, "", "DEBUG"], [4, 2, 1, "", "ERROR"], [4, 2, 1, "", "INFO"], [4, 2, 1, "", "WARNING"], [4, 3, 1, "", "__init__"]]}, "objtypes": {"0": "py:module", "1": "py:class", "2": "py:attribute", "3": "py:method", "4": "py:function"}, "objnames": {"0": ["py", "module", "Python module"], "1": ["py", "class", "Python class"], "2": ["py", "attribute", "Python attribute"], "3": ["py", "method", "Python method"], "4": ["py", "function", "Python function"]}, "titleterms": {"compon": [0, 1, 3], "The": 1, "manag": 1, "abstract": 1, "add": 1, "new": 1, "profil": 1, "nemesi": [2, 7], "util": 2, "how": 2, "us": [2, 5], "modul": 2, "overview": [3, 4], "usag": [3, 4], "ipc": [4, 6], "get": 5, "start": 5, "system": 5, "requir": 5, "run": 5, "thi": 5, "project": 5, "instal": 5, "docker": 5, "compos": 5, "cli": 5, "configur": 5, "interpret": 5, "document": [5, 7], "rout": 6, "log": 6, "state": 6, "set": 6, "event": 6, "current": 6, "other": 6, "sensor": 6, "air": 7, "indic": 7, "tabl": 7, "custom": 6}, "envversion": {"sphinx.domains.c": 2, "sphinx.domains.changeset": 1, "sphinx.domains.citation": 1, "sphinx.domains.cpp": 8, "sphinx.domains.index": 1, "sphinx.domains.javascript": 2, "sphinx.domains.math": 2, "sphinx.domains.python": 3, "sphinx.domains.rst": 2, "sphinx.domains.std": 2, "sphinx": 57}, "alltitles": {"Components": [[0, "components"]], "The Manager": [[1, "the-manager"]], "Abstract": [[1, "abstract"]], "Add new components and profiles": [[1, "add-new-components-and-profiles"]], "Nemesis utilities": [[2, "nemesis-utilities"]], "How to use": [[2, "how-to-use"]], "Modules": [[2, "modules"]], "Component": [[3, "module-src.nemesis_utilities.utilities.component"]], "Overview & Usage": [[3, "overview-usage"], [4, "overview-usage"]], "IPC": [[4, "module-src.nemesis_utilities.utilities.ipc"]], "Getting Started": [[5, "getting-started"]], "System Requirements": [[5, "system-requirements"]], "Run this project": [[5, "run-this-project"]], "Install system requirements": [[5, "install-system-requirements"]], "Docker & Compose": [[5, "docker-compose"]], "Run the project using cli": [[5, "run-the-project-using-cli"]], "Configure interpreter": [[5, "configure-interpreter"]], "Document this project": [[5, "document-this-project"]], "Nemesis Air Documentation": [[7, "nemesis-air-documentation"]], "Indices and tables": [[7, "indices-and-tables"]], "IPC Routes": [[6, "ipc-routes"]], "Logs": [[6, "logs"]], "State": [[6, "state"]], "Set": [[6, "set"]], "Events": [[6, "events"]], "Current state": [[6, "current-state"]], "Other": [[6, "other"]], "Custom States": [[6, "custom-states"]], "Sensors": [[6, "sensors"]]}, "indexentries": {}})