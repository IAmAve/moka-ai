
import sys, os
sys.path.insert(0, r'D:/Ave/Documents/PROJECTS/moka-ai')
sys.path.insert(0, r'D:/Ave/Documents/PROJECTS/moka-ai\\installer')
os.chdir(r'D:/Ave/Documents/PROJECTS/moka-ai')

from installer_wizard.api import WizardAPI
api = WizardAPI()

# Simulate hardware scan
api.set_install_path("D:\\test")
api.scan_hardware()

import json
result = api.get_models(8)
print(json.dumps(result, indent=2))
