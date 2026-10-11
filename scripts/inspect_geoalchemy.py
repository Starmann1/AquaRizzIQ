import inspect
from geoalchemy2 import Geometry

sig = inspect.signature(Geometry.__init__)
print("Geometry.__init__ parameters:")
for param in sig.parameters.values():
    print(f"  {param.name}: default={param.default}")
