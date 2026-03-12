#!/usr/bin/env python3
"""
Ramo Pub v2.1 - Professional Launch Script
Modern Restaurant Management System Entry Point
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class Colors:
    """Terminal colors for professional UI"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_banner():
    """Display professional ASCII banner"""
    banner = f"""
{Colors.BOLD}{Colors.CYAN}
================================================================
                    RAMO PUB & TEAHOUSE
                Restaurant Management System
                        Version 2.1
================================================================
{Colors.BOLD}{Colors.BLUE}
* Modern ERP Solution for Restaurant Excellence
* Luxury Standards | Professional Architecture
* High Performance | Real-time Operations{Colors.ENDC}
"""
    print(banner)


def print_menu():
    """Display main menu"""
    menu = f"""
{Colors.BOLD}{Colors.YELLOW}
================================================================
                    LAUNCH OPTIONS
================================================================

  {Colors.GREEN}[1]{Colors.ENDC} {Colors.CYAN}Start Web Server{Colors.ENDC}           {Colors.YELLOW}Flask API & Dashboard{Colors.ENDC}
  {Colors.GREEN}[2]{Colors.ENDC} {Colors.CYAN}Start Desktop App{Colors.ENDC}           {Colors.YELLOW}PyQt6 GUI Interface{Colors.ENDC}
  {Colors.GREEN}[3]{Colors.ENDC} {Colors.CYAN}FULL LAUNCH{Colors.ENDC}                {Colors.YELLOW}Web API + Desktop App{Colors.ENDC}
  {Colors.GREEN}[4]{Colors.ENDC} {Colors.CYAN}Run Tests{Colors.ENDC}                  {Colors.YELLOW}Quality Assurance{Colors.ENDC}
  {Colors.GREEN}[5]{Colors.ENDC} {Colors.CYAN}System Status{Colors.ENDC}              {Colors.YELLOW}Health Check{Colors.ENDC}
  {Colors.GREEN}[6]{Colors.ENDC} {Colors.CYAN}Exit{Colors.ENDC}                     {Colors.YELLOW}Quit Application{Colors.ENDC}

================================================================
{Colors.ENDC}
"""
    print(menu)


def setup_environment():
    """Setup environment variables for all processes"""
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{PROJECT_ROOT}/src;{PROJECT_ROOT}"
    return env


def start_web_server_background():
    """Start Flask Web Server in background thread"""

    def web_server_thread():
        try:
            env = setup_environment()
            subprocess.run([sys.executable, "-m", "src.web.app"],
                           env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}ERROR: Web Server failed: {e}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}ERROR: Web Server error: {e}{Colors.ENDC}")

    web_thread = threading.Thread(target=web_server_thread, daemon=True)
    web_thread.start()
    return web_thread


def start_web_server():
    """Start Flask Web Server"""
    print(f"\n{Colors.GREEN}Web Starting...{Colors.ENDC}")
    print(f"{Colors.CYAN}   http://localhost:5000{Colors.ENDC}")
    print(f"{Colors.YELLOW}   Press Ctrl+C to stop{Colors.ENDC}\n")

    try:
        env = setup_environment()
        subprocess.run([sys.executable, "-m", "src.web.app"], env=env, check=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Web Server stopped{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.RED}ERROR: Web Server failed: {e}{Colors.ENDC}")


def start_desktop_app():
    """Start PyQt6 Desktop Application"""
    print(f"\n{Colors.GREEN}Desktop Starting...{Colors.ENDC}")
    print(f"{Colors.CYAN}   GUI Interface{Colors.ENDC}")
    print(f"{Colors.YELLOW}   Requires Web Server running on port 5000{Colors.ENDC}\n")

    try:
        env = setup_environment()
        subprocess.run([sys.executable, "main.py"], env=env, check=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Desktop App stopped{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.RED}ERROR: Desktop App failed: {e}{Colors.ENDC}")


def full_launch():
    """Start both Web Server and Desktop App"""
    print(f"\n{Colors.GREEN}FULL LAUNCH INITIATED{Colors.ENDC}")
    print(f"{Colors.CYAN}   Starting Web Server (Background){Colors.ENDC}")
    print(f"{Colors.YELLOW}   Starting Desktop App (Foreground){Colors.ENDC}")

    try:
        web_thread = start_web_server_background()

        print(f"{Colors.YELLOW}Waiting for Web Server to start...{Colors.ENDC}")
        time.sleep(3)

        if web_thread.is_alive():
            print(f"{Colors.GREEN}OK: Web Server is running{Colors.ENDC}")
        else:
            print(f"{Colors.RED}ERROR: Web Server failed to start{Colors.ENDC}")
            return

        print(f"{Colors.CYAN}Starting Desktop App...{Colors.ENDC}")

        env = setup_environment()
        subprocess.run([sys.executable, "main.py"], env=env, check=True)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Full Launch stopped{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.RED}ERROR: Full Launch failed: {e}{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}ERROR: Unexpected error: {e}{Colors.ENDC}")


def run_tests():
    """Run Test Suite"""
    print(f"\n{Colors.GREEN}Running Test Suite...{Colors.ENDC}")

    try:
        env = setup_environment()
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"],
                                capture_output=True, text=True, env=env)
        print(result.stdout)
        if result.stderr:
            print(f"{Colors.YELLOW}Warnings:{Colors.ENDC}\n{result.stderr}")

        if result.returncode == 0:
            print(f"{Colors.GREEN}OK: All tests passed!{Colors.ENDC}")
        else:
            print(f"{Colors.RED}ERROR: Some tests failed{Colors.ENDC}")

    except subprocess.CalledProcessError:
        print(f"{Colors.YELLOW}Pytest not available, running E2E test...{Colors.ENDC}")
        try:
            env = setup_environment()
            result = subprocess.run([sys.executable, "test_e2e_logic.py"],
                                    capture_output=True, text=True, env=env)
            print(result.stdout)
            if result.returncode == 0:
                print(f"{Colors.GREEN}OK: E2E test passed!{Colors.ENDC}")
            else:
                print(f"{Colors.RED}ERROR: E2E test failed{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}ERROR: Test execution failed: {e}{Colors.ENDC}")


def system_status():
    """Display System Health Check"""
    print(f"\n{Colors.GREEN}System Health Check{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.ENDC}")

    print(f"{Colors.YELLOW}Python Version:{Colors.ENDC} {sys.version}")

    dirs_to_check = ['src', 'src/web', 'src/desktop', 'src/core', 'docs', 'scripts']
    for dir_name in dirs_to_check:
        path = PROJECT_ROOT / dir_name
        status = f"{Colors.GREEN}OK{Colors.ENDC}" if path.exists() else f"{Colors.RED}ERROR{Colors.ENDC}"
        print(f"{Colors.YELLOW}Directory {dir_name}:{Colors.ENDC} {status}")

    files_to_check = ['main.py', 'src/web/app.py', 'requirements.txt', '.env.example', 'run.py']
    for file_name in files_to_check:
        path = PROJECT_ROOT / file_name
        status = f"{Colors.GREEN}OK{Colors.ENDC}" if path.exists() else f"{Colors.RED}ERROR{Colors.ENDC}"
        print(f"{Colors.YELLOW}File {file_name}:{Colors.ENDC} {status}")

    print(f"{Colors.CYAN}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.GREEN}OK: System check completed{Colors.ENDC}")


def main():
    """Main application loop"""
    print_banner()

    while True:
        print_menu()

        try:
            choice = input(f"{Colors.BOLD}{Colors.YELLOW}Enter your choice [1-6]: {Colors.ENDC}")

            if choice == '1':
                start_web_server()
            elif choice == '2':
                start_desktop_app()
            elif choice == '3':
                full_launch()
            elif choice == '4':
                run_tests()
            elif choice == '5':
                system_status()
            elif choice == '6':
                print(f"\n{Colors.GREEN}Goodbye!{Colors.ENDC}")
                break
            else:
                print(f"\n{Colors.RED}ERROR: Invalid choice. Please select 1-6.{Colors.ENDC}")

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Exiting...{Colors.ENDC}")
            break
        except Exception as e:
            print(f"\n{Colors.RED}ERROR: {e}{Colors.ENDC}")

        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")


if __name__ == "__main__":
    main()
