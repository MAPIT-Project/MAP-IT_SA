import sys
import logging
from pathlib import Path

## gets the show on the road.
def main():
    print("Hello MAPIT")
    
if __name__ == "__main__":
    #initiate logging as quickly as possible!
    Path('./log/').mkdir(exist_ok=True)
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='log/MAPIT.log', filemode="a", encoding='utf-8', level=logging.INFO)
    sys.exit(main())



