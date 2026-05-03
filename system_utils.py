import platform
import psutil
import socket
import json
import subprocess

try:
    import cpuinfo
except ImportError:
    cpuinfo = None

try:
    import GPUtil
except ImportError:
    GPUtil = None

def get_os_info():
    return {
        "sistema": platform.system(),  # Windows, Linux, Darwin
        "versao": platform.version(),
        "release": platform.release(),
        "arquitetura": platform.machine(),
    }

def get_cpu_info():
    info = {
        "nucleos_fisicos": psutil.cpu_count(logical=False),
        "nucleos_logicos": psutil.cpu_count(logical=True),
    }

    if cpuinfo:
        try:
            cpu = cpuinfo.get_cpu_info()
            info["modelo"] = cpu.get("brand_raw", platform.processor())
        except:
            info["modelo"] = platform.processor()
    else:
        info["modelo"] = platform.processor()

    return info

def get_ram_info():
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024**3), 2),
        "disponivel_gb": round(mem.available / (1024**3), 2),
    }

def get_disk_info():
    disks = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "dispositivo": part.device,
                "ponto_montagem": part.mountpoint,
                "filesystem": part.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "uso_percentual": usage.percent,
            })
        except (PermissionError, OSError):
            continue
    return disks

def get_gpu_info():
    gpus = []

    # tentativa via GPUtil (NVIDIA)
    if GPUtil:
        try:
            for gpu in GPUtil.getGPUs():
                gpus.append({
                    "nome": gpu.name,
                    "memoria_total_mb": gpu.memoryTotal,
                })
        except Exception:
            pass

    # fallback macOS
    if not gpus and platform.system() == "Darwin":
        try:
            # On macOS, system_profiler is more reliable
            output = subprocess.check_output(
                "system_profiler SPDisplaysDataType",
                shell=True
            ).decode()
            # Extract Chipset Model
            for line in output.split("\n"):
                if "Chipset Model" in line:
                    gpus.append({"nome": line.split(":")[1].strip()})
        except Exception:
            pass
            
    # fallback Linux
    if not gpus and platform.system() == "Linux":
        try:
            output = subprocess.check_output("lspci", shell=True).decode()
            for line in output.split("\n"):
                if "VGA" in line or "3D" in line:
                    gpus.append({"nome": line})
        except Exception:
            pass

    # fallback Windows
    if not gpus and platform.system() == "Windows":
        try:
            output = subprocess.check_output(
                "wmic path win32_VideoController get name",
                shell=True
            ).decode()
            gpus = [{"nome": line.strip()} for line in output.split("\n") if line.strip() and "Name" not in line]
        except Exception:
            pass

    return gpus

def get_network_info():
    try:
        hostname = socket.gethostname()
        ip_local = socket.gethostbyname(hostname)
    except:
        hostname = "Unknown"
        ip_local = "127.0.0.1"
    return {
        "hostname": hostname,
        "ip_local": ip_local,
    }

def get_system_info():
    """Retrieve comprehensive hardware and OS information."""
    return {
        "os": get_os_info(),
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "disco": get_disk_info(),
        "gpu": get_gpu_info(),
        "rede": get_network_info(),
    }
