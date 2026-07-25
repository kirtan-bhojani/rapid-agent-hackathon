import sys, os
sys.path.append(os.getcwd())
from tools.search_tool import search_universities
print(search_universities('Master in AI Germany'))
