"""Find PromptMessage in the Phoenix SDK."""
import importlib, inspect

# Search for PromptMessage across the package
import phoenix.client.types.prompts as pt
print("=== prompts module dir:", [x for x in dir(pt) if not x.startswith('_')])

# Check the source of PromptVersion.__init__
src = inspect.getsource(pt.PromptVersion.__init__)
print("=== PromptVersion.__init__ source:\n", src[:2000])

# Find the annotation type
hints = pt.PromptVersion.__init__.__annotations__
print("=== init annotations:", hints)

# Try to locate the module of the 'prompt' parameter
prompt_type = hints.get('prompt')
print("=== prompt type annotation:", prompt_type)

# Search for PromptMessage
import phoenix.client.types as pct
print("\n=== phoenix.client.types dir:", [x for x in dir(pct) if not x.startswith('_')])
print("=== phoenix.client.types __all__:", getattr(pct, '__all__', 'N/A'))

# Check submodules
import pkgutil
pkg_path = pct.__path__ if hasattr(pct, '__path__') else []
for importer, modname, ispkg in pkgutil.walk_packages(pkg_path, prefix='phoenix.client.types.'):
    print(f"  submodule: {modname}")
