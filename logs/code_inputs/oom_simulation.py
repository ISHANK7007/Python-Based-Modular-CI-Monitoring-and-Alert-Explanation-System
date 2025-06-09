def allocate_big_list():
    x = []
    while True:
        x.append('A' * 10**6)

if __name__ == "__main__":
    allocate_big_list()