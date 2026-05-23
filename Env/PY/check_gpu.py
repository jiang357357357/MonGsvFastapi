import platform
import subprocess
import sys


def print_header(title: str) -> None:
    print("=" * 40)
    print(title)
    print("=" * 40)


def main() -> int:
    print_header("GPU Environment Check")
    print(f"python={sys.version.split()[0]}")
    print(f"platform={platform.platform()}")
    print(f"architecture={platform.architecture()[0]}")

    try:
        import torch
    except Exception as exc:
        print(f"torch_import_error={exc}")
        return 1

    print(f"torch={torch.__version__}")
    print(f"torch_cuda={torch.version.cuda}")
    print(f"cuda_available={torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"gpu_name={torch.cuda.get_device_name(0)}")
        print(f"gpu_count={torch.cuda.device_count()}")
    else:
        print("gpu_name=no gpu")

    try:
        result = subprocess.run(
            ["nvidia-smi"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        print("")
        print("nvidia_smi:")
        if result.stdout:
            print(result.stdout.strip())
        elif result.stderr:
            print(result.stderr.strip())
        else:
            print("no output")
    except FileNotFoundError:
        print("")
        print("nvidia_smi:")
        print("nvidia-smi not found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
