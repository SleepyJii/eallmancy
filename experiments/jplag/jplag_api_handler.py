import subprocess
import atexit
import os
import signal
import time
import requests


class JPlagApiHandler:
    def __init__(self, jar_path=None, port=8080, max_startup_wait=5, auto_start=True):
        self.process = None
        self.jar_path = jar_path or os.path.abspath("/root/eallmancy/experiments/jplag/jplag-api")
        self.port = port
        self._max_startup_wait = max_startup_wait
        self._cleaned_up = False

        if auto_start:
            self.start()
    
    @property
    def is_alive(self):
        if self.process is not None:
            retcode = self.process.poll()
            return retcode is None
        else:
            return False

    def start(self):
        if self.is_alive:
            print("not relaunching JPlag API, was still alive")
            return
        return self._launch_jplag_api()

    def _launch_jplag_api(self):
        # Start the Java API
        self.process = subprocess.Popen(
            ["java", "-jar", self.jar_path, f"--port={self.port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        connection_attempts = 0
        while connection_attempts < self._max_startup_wait:
            try:
                resp = requests.get('http://localhost:8080')
                break
            except requests.ConnectionError as ce:
                connection_attempts += 1
                time.sleep(1)
                continue
            except Exception as e:
                raise Exception(e)
        self._cleaned_up = False
        atexit.register(self.cleanup)
        print(f"JPlag API started on port {self.port}, pid={self.process.pid}")

# Ensure the subprocess is terminated on Python shutdown
    def cleanup(self):
        if self._cleaned_up:
            return
        else:
            self._cleaned_up = True
        
        print("Shutting down JPlag API...")
        if self.process.poll() is None:  # still running
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        print("Shutdown complete.")

    def __del__(self):
        self.cleanup()
