from typing import ChainMap


class MultiLevel(ChainMap):
    """Use multiple caches, where we assume the first is the fastest"""

    def __getitem__(self, key):
        for level, mapping in enumerate(self.maps):
            try:
                value = mapping[key]
                # write back to lower levels
                for i in range(level):
                    self.maps[i][key] = value
                return value
            except KeyError:
                pass
        return self.__missing__(key)

    def __setitem__(self, key, value):
        for cache in self.maps:
            cache[key] = value

    def __delitem__(self, key):
        for cache in self.maps:
            del cache[key]
