import multiprocessing


def default_max_processes() -> int:
    return int(1.0 * multiprocessing.cpu_count())
