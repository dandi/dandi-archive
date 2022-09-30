import os


def extract_paths(path: str) -> list[str]:
    nodepaths: list[str] = path.split('/')
    for i in range(len(nodepaths))[1:]:
        nodepaths[i] = os.path.join(nodepaths[i - 1], nodepaths[i])

    return nodepaths
