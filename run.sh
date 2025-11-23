# Build C++ extension
pip install -e host/engine/ || { echo "Build failed"; exit 1; }

venv/bin/python3 host/engine/groovebox/main.py