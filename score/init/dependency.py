from .exceptions import DependencyLoop


class DependencySolver:
    """
    A simple helper for resolving module interdependencies. Basic usage:

    .. code-block:: python

      solver = DependencySolver()
      solver.add_dependency('a', 'b')  # a depends on b
      solver.add_dependency('b', 'c')  # b depends on c
      solver.solve()  # returns all modules in the order in which they
                      # should be initialized: ['c', 'b', 'a']
    """

    def __init__(self):
        self._dependencies = dict()

    def add_dependency(self, from_, to=None):
        """
        Add dependency from module *from_* to module *to*. If a module has no
        dependencies, you can still register it without a *to* argument to
        ensure that it is included in the result set of the solve() call.
        """
        if from_ not in self._dependencies:
            self._dependencies[from_] = set()
        if to is not None:
            self._dependencies[from_].add(to)

    add = add_dependency

    def remove_dependency(self, from_, to):
        """
        Removes a direct dependency. Does nothing, if there was no such
        dependency.
        """
        if from_ not in self._dependencies:
            return
        self._dependencies[from_].difference_update({to})

    def direct_dependencies(self, node):
        """
        Provides the direct dependencies of a given node.
        """
        return list(self.direct_dependencies_iter(node))

    def direct_dependencies_iter(self, node):
        """
        Same as :meth:`direct_dependencies`, but returns an iterator.
        """
        if node not in self._dependencies:
            return
        yield from self._dependencies[node]

    def direct_dependents(self, node):
        """
        Provides all modules that directly depend on this one.
        """
        return list(self.direct_dependents_iter(node))

    def direct_dependents_iter(self, node, *, __visited=None):
        """
        Same as :meth:`direct_dependents`, but returns an iterator.
        """
        if node not in self._dependencies:
            return
        for other, other_deps in self._dependencies.items():
            if other == node or node not in other_deps:
                continue
            yield other

    def has_direct_dependency(self, from_, to):
        """
        Tests, if given node *from_* has a direct dependency to node *to*.
        """
        return from_ in self._dependencies and to in self._dependencies[from_]

    def solve(self):
        """
        Solves the dependency system.
        """
        sorted_ = []
        dependencies = dict()
        for item, item_dependencies in self._dependencies.items():
            if not item_dependencies:
                sorted_.append(item)
            else:
                dependencies[item] = item_dependencies
                for dep in item_dependencies:
                    if dep not in self._dependencies:
                        sorted_.append(dep)
        updated = True
        while updated:
            updated = False
            for item in list(dependencies.keys()):
                deps = dependencies[item]
                to_remove = deps.intersection(sorted_)
                if not to_remove:
                    continue
                updated = True
                if to_remove == deps:
                    sorted_.append(item)
                    del dependencies[item]
                else:
                    deps.difference_update(sorted_)
        if dependencies:
            item = next(iter(dependencies.keys()))
            loop = [item, dependencies[item].pop()]
            while loop[-1] not in loop[:-1]:
                loop.append(dependencies[loop[-1]].pop())
            raise DependencyLoop(loop)
        return sorted_
