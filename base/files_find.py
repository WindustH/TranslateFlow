# version 1.1
import os

def Match(root,file, extensions={}, exclusions={}):
    for exclusion in exclusions:
        if exclusion in root or exclusion in file:
            return False
    if len(extensions)==0:
        return True
    for extension in extensions:
        if extension in file:
            return True
    return False;

# 保留文件夹结构
# 在输入文件夹及其子文件夹搜索文件，给出到输出文件夹的路径
# 若 mkdir 为真，提前创建目标文件需要的文件夹
def Files(input_root, output_root, extensions={}, exclusions={},mkdir=True):
    input_paths = []
    output_paths = []
    for root, lists, files in os.walk(input_root):
        for file in files:
            if Match(root,file,extensions, exclusions):
                input_path = os.path.join(root, file)
                output_dir = os.path.join(output_root,
                                            root[len(input_root) + 1:])
                if not os.path.exists(output_dir) and mkdir:
                    os.makedirs(output_dir)
                output_path = os.path.join(output_dir, file)
                input_paths.append(input_path)
                output_paths.append(output_path)
    return input_paths, output_paths


# 不保留文件夹结构
# 在输入文件夹及其子文件夹搜索文件，给出到输出文件夹的路径
# 若 mkdir 为真，提前创建目标文件需要的文件夹
def FilesOnly(input_root, output_root, extensions={}, exclusions={},mkdir=True):
    input_paths = []
    output_paths = []
    for root, lists, files in os.walk(input_root):
        for file in files:
            if Match(root,file,extensions, exclusions):
                input_path = os.path.join(root, file)
                if not os.path.exists(output_root) and mkdir:
                    os.makedirs(output_root)
                output_path = os.path.join(output_root, file)
                input_paths.append(input_path)
                output_paths.append(output_path)
    return input_paths, output_paths