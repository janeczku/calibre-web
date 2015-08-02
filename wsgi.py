
import os
import sys
base_path = os.path.dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.append(os.path.join(base_path, 'lib'))

from cps import web
from cps import config

global title_sort

def title_sort(title):
    return title

if __name__ == "__main__":
    web.app.run(host="0.0.0.0",port=config.PORT, debug=True)
