import os
import sys
import shlex
import signal
import subprocess
import time
import heapq
from collections import deque, namedtuple

# ---------- Process Scheduling Data Structures ----------
Process = namedtuple('Process', ['pid', 'name', 'burst_time', 'priority'])

class Scheduler:
    def __init__(self):
        self.process_queue = deque()
        self.priority_queue = []
        self.pid_counter = 1

    def add_process(self, name, burst_time, priority=0):
        process = Process(self.pid_counter, name, burst_time, priority)
        self.process_queue.append(process)
        heapq.heappush(self.priority_queue, (priority, self.pid_counter, process))
        self.pid_counter += 1
        print(f"Process added: {process}")

    def round_robin(self, time_slice):
        print("\n[Round-Robin Scheduling]")
        queue = deque(self.process_queue)
        waiting_time = {}
        turnaround_time = {}
        response_time = {}
        start_times = {}
        t = 0

        while queue:
            process = queue.popleft()
            remaining_time = min(process.burst_time, time_slice)

            if process.pid not in start_times:
                start_times[process.pid] = t
                response_time[process.pid] = t

            print(f"Running {process.name} (PID={process.pid}) for {remaining_time} units")
            time.sleep(0.1)
            t += remaining_time
            remaining_burst = process.burst_time - remaining_time

            if remaining_burst > 0:
                queue.append(Process(process.pid, process.name, remaining_burst, process.priority))
            else:
                turnaround_time[process.pid] = t
                waiting_time[process.pid] = turnaround_time[process.pid] - process.burst_time

        self._print_metrics(waiting_time, turnaround_time, response_time)

    def priority_scheduling(self):
        print("\n[Priority-Based Scheduling]")
        t = 0
        waiting_time = {}
        turnaround_time = {}
        response_time = {}

        while self.priority_queue:
            _, _, process = heapq.heappop(self.priority_queue)
            response_time[process.pid] = t
            print(f"Running {process.name} (PID={process.pid}, Priority={process.priority}) for {process.burst_time} units")
            time.sleep(0.1)
            t += process.burst_time
            turnaround_time[process.pid] = t
            waiting_time[process.pid] = t - process.burst_time

        self._print_metrics(waiting_time, turnaround_time, response_time)

    def _print_metrics(self, waiting, turnaround, response):
        print("\nPerformance Metrics:")
        for pid in waiting:
            print(f"PID={pid}: Waiting={waiting[pid]}, Turnaround={turnaround[pid]}, Response={response[pid]}")

# ---------- Shell Implementation ----------
class Job:
    def __init__(self, pid, command):
        self.pid = pid
        self.command = command

jobs = deque()
scheduler = Scheduler()

# Built-in command implementations
def shell_cd(args): ...
def shell_pwd(args): print(os.getcwd())
def shell_exit(): sys.exit(0)
def shell_echo(args): print(' '.join(args[1:]))
def shell_clear(args): os.system('cls' if os.name == 'nt' else 'clear')
def shell_ls(args): print('\n'.join(os.listdir('.')))
def shell_cat(args):
    try:
        with open(args[1], 'r') as file:
            print(file.read())
    except IndexError:
        print("cat: missing filename")
    except FileNotFoundError:
        print("cat: file not found")

def shell_mkdir(args): ...
def shell_rmdir(args): ...
def shell_rm(args): ...
def shell_touch(args):
    try:
        open(args[1], 'a').close()
    except IndexError:
        print("touch: missing file name")

def shell_kill(args):
    try:
        os.kill(int(args[1]), signal.SIGTERM)
    except (IndexError, ValueError):
        print("kill: invalid or missing PID")

def shell_jobs(args):
    for i, job in enumerate(jobs):
        try:
            os.kill(job.pid, 0)
            print(f"[{i+1}] {job.pid} {job.command}")
        except ProcessLookupError:
            continue

def shell_fg(args):
    try:
        job_id = int(args[1]) - 1
        job = jobs.pop(job_id)
        os.waitpid(job.pid, 0)
    except Exception:
        print("fg: error bringing job to foreground")

def shell_bg(args):
    try:
        job_id = int(args[1]) - 1
        job = jobs[job_id]
        os.kill(job.pid, signal.SIGCONT)
    except Exception:
        print("bg: error resuming job")

# --- NEW Built-ins for Scheduling ---
def shell_addproc(args):
    try:
        name = args[1]
        burst = int(args[2])
        priority = int(args[3]) if len(args) > 3 else 0
        scheduler.add_process(name, burst, priority)
    except (IndexError, ValueError):
        print("Usage: addproc <name> <burst_time> [priority]")

def shell_schedule(args):
    if len(args) < 2:
        print("Usage: schedule [rr|priority] [time_slice]")
        return
    if args[1] == "rr":
        ts = int(args[2]) if len(args) > 2 else 2
        scheduler.round_robin(ts)
    elif args[1] == "priority":
        scheduler.priority_scheduling()
    else:
        print("Unknown scheduling type")

# Command executor
def execute_command(args):
    if not args:
        return

    builtins = {
        'cd': shell_cd,
        'pwd': shell_pwd,
        'exit': shell_exit,
        'echo': shell_echo,
        'clear': shell_clear,
        'ls': shell_ls,
        'cat': shell_cat,
        'mkdir': shell_mkdir,
        'rmdir': shell_rmdir,
        'rm': shell_rm,
        'touch': shell_touch,
        'kill': shell_kill,
        'jobs': shell_jobs,
        'fg': shell_fg,
        'bg': shell_bg,
        'addproc': shell_addproc,
        'schedule': shell_schedule
    }

    command = args[0]

    if command in builtins:
        builtins[command](args)
    else:
        background = args[-1] == '&'
        if background:
            args = args[:-1]
        try:
            proc = subprocess.Popen(args)
            if background:
                jobs.append(Job(proc.pid, ' '.join(args)))
                print(f"Started background job {proc.pid}")
            else:
                proc.wait()
        except FileNotFoundError:
            print(f"{command}: command not found")
        except Exception as e:
            print(f"Error executing command: {e}")

def shell_loop():
    while True:
        try:
            command_line = input("PyShell> ")
            args = shlex.split(command_line)
            execute_command(args)
        except EOFError:
            break
        except KeyboardInterrupt:
            print()

if __name__ == '__main__':
    shell_loop()
