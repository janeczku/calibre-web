# -*- coding: utf-8 -*-

"""
Audiobook Setup Module
Auto-installs Node.js dependencies for audiobook generation
"""

import os
import sys
import subprocess
import shutil
from . import logger

log = logger.create()


class AudiobookSetup:
    """Handles installation and verification of audiobook dependencies"""

    @staticmethod
    def check_node_installed():
        """Check if Node.js is installed"""
        return shutil.which('node') is not None

    @staticmethod
    def check_npm_installed():
        """Check if npm is installed"""
        return shutil.which('npm') is not None

    @staticmethod
    def check_espeak_installed():
        """Check if espeak-ng or espeak is installed (Linux TTS)"""
        return shutil.which('espeak-ng') is not None or shutil.which('espeak') is not None

    @staticmethod
    def check_festival_installed():
        """Check if festival is installed (Linux TTS alternative)"""
        return shutil.which('festival') is not None

    @staticmethod
    def check_say_installed():
        """Check if 'say' library is installed"""
        try:
            result = subprocess.run(
                ['npm', 'list', '-g', 'say'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return 'say@' in result.stdout
        except Exception as e:
            log.error(f"Error checking 'say' installation: {e}")
            return False

    @staticmethod
    def install_say():
        """Install 'say' library globally"""
        try:
            log.info("Installing 'say' library from npm...")

            # Try global installation
            result = subprocess.run(
                ['npm', 'install', '-g', 'say'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                log.info("'say' library installed successfully (global)")
                return True
            else:
                log.warning(f"Global installation failed: {result.stderr}")
                log.info("Trying local installation...")

                # Fallback to local installation
                calibre_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                result = subprocess.run(
                    ['npm', 'install', 'say'],
                    cwd=calibre_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode == 0:
                    log.info("'say' library installed successfully (local)")
                    return True
                else:
                    log.error(f"Local installation also failed: {result.stderr}")
                    return False

        except subprocess.TimeoutExpired:
            log.error("Installation timed out after 120 seconds")
            return False
        except Exception as e:
            log.error(f"Error installing 'say': {e}")
            return False

    @staticmethod
    def setup_audiobook_dependencies():
        """
        Main setup function - checks and installs dependencies if needed
        Returns: (success, message)
        """
        # Check Node.js
        if not AudiobookSetup.check_node_installed():
            msg = "Node.js is not installed. Audiobook generation will not be available. " \
                  "Please install from: https://nodejs.org/"
            log.warning(msg)
            return False, msg

        # Check npm
        if not AudiobookSetup.check_npm_installed():
            msg = "npm is not installed. Please reinstall Node.js from: https://nodejs.org/"
            log.warning(msg)
            return False, msg

        # Detect platform
        platform = sys.platform

        # On Linux, check for espeak-ng/espeak or festival
        if platform.startswith('linux'):
            if AudiobookSetup.check_espeak_installed():
                log.info("espeak-ng/espeak found - audiobook generation available (Linux TTS)")
                return True, "Audiobook dependencies OK (espeak)"
            elif AudiobookSetup.check_festival_installed():
                log.info("festival found - audiobook generation available (Linux TTS)")
                return True, "Audiobook dependencies OK (festival)"
            else:
                msg = "No Linux TTS engine found. Please install espeak-ng: apt-get install espeak-ng"
                log.warning(msg)
                return False, msg

        # On macOS/Windows, check for 'say' library
        # Check if 'say' is already installed
        if AudiobookSetup.check_say_installed():
            log.info("'say' library is already installed - audiobook generation available")
            return True, "Audiobook dependencies OK"

        # Try to install 'say'
        log.info("'say' library not found - attempting automatic installation...")

        if AudiobookSetup.install_say():
            # Verify installation
            if AudiobookSetup.check_say_installed():
                msg = "'say' library installed successfully - audiobook generation is now available"
                log.info(msg)
                return True, msg
            else:
                msg = "Installation appeared to succeed but 'say' still not found. " \
                      "Try manually: npm install -g say"
                log.error(msg)
                return False, msg
        else:
            msg = "Failed to install 'say' library automatically. " \
                  "Please install manually: npm install -g say"
            log.error(msg)
            return False, msg

    @staticmethod
    def get_status():
        """Get current status of audiobook dependencies"""
        status = {
            'node_installed': AudiobookSetup.check_node_installed(),
            'npm_installed': AudiobookSetup.check_npm_installed(),
            'say_installed': AudiobookSetup.check_say_installed(),
            'ready': False
        }

        status['ready'] = all([
            status['node_installed'],
            status['npm_installed'],
            status['say_installed']
        ])

        return status

    @staticmethod
    def get_node_version():
        """Get installed Node.js version"""
        try:
            result = subprocess.run(
                ['node', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None

    @staticmethod
    def get_say_version():
        """Get installed 'say' version"""
        try:
            result = subprocess.run(
                ['npm', 'list', '-g', 'say'],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse version from output
            for line in result.stdout.split('\n'):
                if 'say@' in line:
                    version = line.split('say@')[1].split()[0]
                    return version
            return None
        except:
            return None


def init_audiobook_dependencies():
    """
    Initialize audiobook dependencies at startup
    This function is called when Calibre-Web starts
    """
    try:
        log.info("Checking audiobook dependencies...")
        success, message = AudiobookSetup.setup_audiobook_dependencies()

        if success:
            node_ver = AudiobookSetup.get_node_version()
            say_ver = AudiobookSetup.get_say_version()
            log.info(f"Audiobook generation ready - Node.js {node_ver}, say {say_ver}")
        else:
            log.warning(f"Audiobook generation not available: {message}")

        return success

    except Exception as e:
        log.error(f"Error initializing audiobook dependencies: {e}")
        return False


def get_audiobook_status_info():
    """Get detailed status information for display in admin panel"""
    status = AudiobookSetup.get_status()

    info = {
        'available': status['ready'],
        'node_installed': status['node_installed'],
        'node_version': AudiobookSetup.get_node_version() if status['node_installed'] else None,
        'npm_installed': status['npm_installed'],
        'say_installed': status['say_installed'],
        'say_version': AudiobookSetup.get_say_version() if status['say_installed'] else None,
    }

    # Generate status message
    if info['available']:
        info['message'] = "Audiobook generation is available and ready"
        info['status'] = "success"
    elif not info['node_installed']:
        info['message'] = "Node.js not installed - install from https://nodejs.org/"
        info['status'] = "error"
    elif not info['say_installed']:
        info['message'] = "Installing 'say' library... (refresh in a moment)"
        info['status'] = "warning"
    else:
        info['message'] = "Unknown status"
        info['status'] = "warning"

    return info
