import os
import multiprocessing

def child_func():
    print(f"Child: TEST_VAR = {os.environ.get('TEST_VAR', 'NOT SET')}")
    print(f"Child: PATH first element = {os.environ.get('PATH', '').split(':')[0]}")

if __name__ == "__main__":
    os.environ['TEST_VAR'] = 'hello_from_parent'
    print(f"Parent: TEST_VAR = {os.environ.get('TEST_VAR')}")

    ctx = multiprocessing.get_context('spawn')
    p = ctx.Process(target=child_func)
    p.start()
    p.join()
