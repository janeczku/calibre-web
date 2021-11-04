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

def dependency_check(optional=False):
    dep = list()
    if importlib or pkgresources:
        if optional:
            req_path = os.path.join(BASE_DIR, "optional-requirements.txt")
        else:
            req_path = os.path.join(BASE_DIR, "requirements.txt")
        if os.path.exists(req_path):
            try:
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
                                else:
                                    return [{'name':res.group(1),
                                            'target': "available",
                                            'found': "Not available"
                                            }]

                            if res.group(2).strip() == "==":
                                if dep_version.split('.') != res.group(3).split('.'):
                                    dep.append({'name': res.group(1),
                                                'found': dep_version,
                                                "target": res.group(2) + res.group(3)})
                                    continue
                            elif res.group(2).strip() == ">=":
                                if dep_version.split('.') < res.group(3).split('.'):
                                    dep.append({'name': res.group(1),
                                                'found': dep_version,
                                                "target": res.group(2) + res.group(3)})
                                    continue
                            elif res.group(2).strip() == ">":
                                if dep_version.split('.') <= res.group(3).split('.'):
                                    dep.append({'name': res.group(1),
                                                'found': dep_version,
                                                "target": res.group(2) + res.group(3)})
                                    continue
                            if res.group(4) and res.group(5):
                                if res.group(4).strip() == "<":
                                    if dep_version.split('.') >= res.group(5).split('.'):
                                        dep.append(
                                            {'name': res.group(1),
                                             'found': dep_version,
                                             "target": res.group(4) + res.group(5)})
                                        continue
                                elif res.group(2).strip() == "<=":
                                    if dep_version.split('.') > res.group(5).split('.'):
                                        dep.append(
                                            {'name': res.group(1),
                                             'found': dep_version,
                                             "target": res.group(4) + res.group(5)})
                                        continue
            except Exception as e:
                print(e)
    return dep
