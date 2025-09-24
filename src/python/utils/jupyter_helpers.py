def start_notebook():
    """Start Jupyter notebook with project settings."""
    import subprocess
    import os
    
    port = os.getenv('JUPYTER_PORT', '8889')
    args = [
        'jupyter', 'notebook',
        f'--port={port}',
        '--no-browser',
        '--notebook-dir=notebooks'
    ]
    subprocess.run(args, check=True)