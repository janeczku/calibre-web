import os
import re

from .constants import BASE_DIR
try:
    from importlib_metadata import version
    importlib = True
    ImportNotFound = BaseException
except ImportError:
    importlib = False


if not importlib:
    try:
        import pkg_resources
        from pkg_resources import DistributionNotFound as ImportNotFound
        pkgresources = True
    except ImportError as e:
        pkgresources = False

def load_dependencys(optional=False):
    deps = list()
    if importlib or pkgresources:
        if optional:
            req_path = os.path.join(BASE_DIR, "optional-requirements.txt")
        else:
            req_path = os.path.join(BASE_DIR, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, 'r') as f:
                for line in f:
                    if not line.startswith('#') and not line == '\n' and not line.startswith('git'):
                        res = re.match(r'(.*?)([<=>\s]+)([\d\.]+),?\s?([<=>\s]+)?([\d\.]+)?', line.strip())
                        try:
                            if importlib:
                                dep_version = version(res.group(1))
                            else:
                                dep_version = pkg_resources.get_distribution(res.group(1)).version
                        except ImportNotFound:
                            if optional:
                                continue
                            dep_version = "not installed"
                        deps.append([dep_version, res.group(1), res.group(2), res.group(3), res.group(4), res.group(5)])
    return deps


def dependency_check(optional=False):
    d = list()
    deps = load_dependencys(optional)
    for dep in deps:
        try:
            dep_version_int = [int(x) for x in dep[0].split('.')]
            low_check = [int(x) for x in dep[3].split('.')]
            high_check = [int(x) for x in dep[5].split('.')]
        except AttributeError:
            high_check = None
        except ValueError:
            d.append({'name': dep[1],
                     'target': "available",
                     'found': "Not available"
                     })
            continue

        if dep[2].strip() == "==":
            if dep_version_int != low_check:
                d.append({'name': dep[1],
                            'found': dep[0],
                            "target": dep[2] + dep[3]})
                continue
        elif dep[2].strip() == ">=":
            if dep_version_int < low_check:
                d.append({'name': dep[1],
                            'found': dep[0],
                            "target": dep[2] + dep[3]})
                continue
        elif dep[2].strip() == ">":
            if dep_version_int <= low_check:
                d.append({'name': dep[1],
                            'found': dep[0],
                            "target": dep[2] + dep[3]})
                continue
        if dep[4] and dep[5]:
            if dep[4].strip() == "<":
                if dep_version_int >= high_check:
                    d.append(
                        {'name': dep[1],
                         'found': dep[0],
                         "target": dep[4] + dep[5]})
                    continue
            elif dep[4].strip() == "<=":
                if dep_version_int > high_check:
                    d.append(
                        {'name': dep[1],
                         'found': dep[0],
                         "target": dep[4] + dep[5]})
                    continue
    return d
