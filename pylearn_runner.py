"""
PyLearn Runner — Real CPython execution engine for Chaquopy
Handles: code execution, pip install, package listing, pygame headless
"""
import sys
import io
import os
import json
import traceback
import subprocess


def run_code(code):
    """
    Execute Python code.
    Returns JSON: {output: str, errors: str, success: bool, images: list}
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    images = []

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stdout_buf
    sys.stderr = stderr_buf

    result = {"output": "", "errors": "", "success": True, "images": []}

    try:
        # Intercept matplotlib show() to capture figures
        exec_globals = {
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }

        # Patch matplotlib if available
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import base64

            def _capture_show(*args, **kwargs):
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=96,
                           bbox_inches='tight', facecolor='#0d0d0d')
                buf.seek(0)
                b64 = base64.b64encode(buf.read()).decode('utf-8')
                images.append(b64)
                plt.close()

            plt.show = _capture_show
            exec_globals['plt'] = plt
            exec_globals['matplotlib'] = matplotlib
        except ImportError:
            pass

        exec(compile(code, '<user_code>', 'exec'), exec_globals)
        result["output"] = stdout_buf.getvalue()
        result["images"] = images

    except SystemExit as e:
        result["output"] = stdout_buf.getvalue()
        result["errors"] = "SystemExit({})".format(e.code)
        result["success"] = False
    except SyntaxError as e:
        result["output"] = stdout_buf.getvalue()
        result["errors"] = "SyntaxError: {} (line {})".format(e.msg, e.lineno)
        result["success"] = False
    except Exception:
        result["output"] = stdout_buf.getvalue()
        result["errors"] = traceback.format_exc()
        result["success"] = False
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return json.dumps(result)


def pip_install(package_name):
    """
    Install a single pip package using real pip.
    Returns JSON: {success: bool, output: str, error: str}
    """
    package_name = package_name.strip()
    if not package_name:
        return json.dumps({"success": False, "output": "", "error": "No package name provided"})

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package_name,
             '--quiet', '--no-cache-dir'],
            capture_output=True,
            text=True,
            timeout=180
        )
        return json.dumps({
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip()
        })
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "output": "",
            "error": "Installation timed out (180s). Try again."
        })
    except Exception as e:
        return json.dumps({"success": False, "output": "", "error": str(e)})


def pip_install_multiple(packages_str):
    """
    Install multiple pip packages (space-separated string).
    Returns JSON array of results.
    """
    packages = packages_str.strip().split()
    results = []
    for pkg in packages:
        r = json.loads(pip_install(pkg))
        r["package"] = pkg
        results.append(r)
    return json.dumps(results)


def pip_list():
    """
    List installed packages.
    Returns JSON array of {name, version} objects.
    """
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=json'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return "[]"
    except Exception:
        # Fallback: list from pkg_resources
        try:
            import pkg_resources
            pkgs = [{"name": d.project_name, "version": d.version}
                    for d in pkg_resources.working_set]
            return json.dumps(pkgs)
        except Exception:
            return "[]"


def python_version():
    """Return Python version string."""
    return "Python {}.{}.{} (Chaquopy — Native Android)".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    )


def can_import(module_name):
    """Check if a module can be imported."""
    try:
        __import__(module_name.strip())
        return "true"
    except ImportError:
        return "false"


def run_pygame_headless(code):
    """
    Run pygame code in headless mode — captures screen as PNG base64.
    Uses pygame's offscreen surface rendering.
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stdout_buf
    sys.stderr = stderr_buf

    result = {"output": "", "errors": "", "success": True, "frame": ""}

    try:
        import pygame
        import base64

        # Force offscreen rendering
        os.environ['SDL_VIDEODRIVER'] = 'offscreen'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'

        exec_globals = {
            "__name__": "__main__",
            "__builtins__": __builtins__,
            "pygame": pygame,
        }

        # Inject frame capture: after pygame.display.flip() or .update()
        # capture the surface to base64
        frames = []

        original_flip = pygame.display.flip
        original_update = pygame.display.update

        def capture_flip():
            try:
                surface = pygame.display.get_surface()
                if surface:
                    buf = io.BytesIO()
                    pygame.image.save(surface, buf, 'PNG')
                    buf.seek(0)
                    frames.append(base64.b64encode(buf.read()).decode())
            except Exception:
                pass

        pygame.display.flip = capture_flip
        pygame.display.update = lambda *a: capture_flip()

        exec(compile(code, '<pygame_code>', 'exec'), exec_globals)

        result["output"] = stdout_buf.getvalue()
        result["frames"] = frames
        if frames:
            result["frame"] = frames[-1]  # Last rendered frame

    except ImportError:
        result["errors"] = "pygame is not installed. Run: pip install pygame-ce"
        result["success"] = False
    except Exception:
        result["output"] = stdout_buf.getvalue()
        result["errors"] = traceback.format_exc()
        result["success"] = False
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return json.dumps(result)
