# -*- coding: utf-8 -*-
# Copyright 2018-2020 The pyXem developers
#
# This file is part of orix.
#
# orix is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# orix is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with orix.  If not, see <http://www.gnu.org/licenses/>.

import copy
from itertools import islice
from collections import OrderedDict

import matplotlib.colors as mcolors
import numpy as np

from orix.quaternion.symmetry import _groups, Symmetry


# All named Matplotlib colors (tableau and xkcd already lower case hex)
ALL_COLORS = mcolors.TABLEAU_COLORS
for k, v in {**mcolors.BASE_COLORS, **mcolors.CSS4_COLORS}.items():
    ALL_COLORS[k] = mcolors.to_hex(v)
ALL_COLORS.update(mcolors.XKCD_COLORS)

# Point group alias mapping
# Why is this needed? E.g., in EDAX TSL OIM Analysis 7.2, point group 432 is
# entered as 43...
POINT_GROUP_ALIASES = {
    '432': '43',
}


class Phase:
    """Name, crystal symmetry, and color of a phase in a crystallographic
    map.

    Attributes
    ----------
    name : str
        Phase name.
    symmetry : orix.quaternion.symmetries.Symmetry
        Crystal symmetries of the phase.
    color : str
        Name of phase color in Matplotlib's list of named colors.
    color_rgb : tuple
        RGB values of phase color, obtained from the color name.

    Methods
    -------
    deepcopy()
        Return a deep copy using :py:func:`~copy.deepcopy` function.
    """

    def __init__(self, name=None, symmetry=None, color=None):
        """
        Parameters
        ----------
        name : str, optional
            Phase name. If ``None`` is passed (default), name is set to
            ``None``.
        symmetry : str, optional
            Point group of phase's crystal symmetry. If ``None`` is passed
            (default), it set to ``None``.
        color : str, optional
            Phase color. If ``None`` is passed (default), it is set to
            'tab:blue' (first among the default Matplotlib colors).
        """
        self.name = name
        self.symmetry = symmetry
        if color is None:
            self.color = "tab:blue"
        else:
            self.color = color

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str) and value is not None:
            raise ValueError(f"Phase name {value} must be of type {str}.")
        else:
            self._name = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        if mcolors.is_color_like(value):
            value_hex = mcolors.to_hex(value)
            for name, color_hex in ALL_COLORS.items():
                if color_hex == value_hex:
                    self._color = name
                    break
        else:
            raise ValueError(
                f"{value} must be in the list of named Matplotlib colors or be "
                "interpreted as an RGB(A) color by "
                "matplotlib.colors.is_color_like()."
            )

    @property
    def color_rgb(self):
        return mcolors.to_rgb(self.color)

    @property
    def symmetry(self):
        return self._symmetry

    @symmetry.setter
    def symmetry(self, value):
        if isinstance(value, str):
            for correct, alias in POINT_GROUP_ALIASES.items():
                if value == alias:
                    value = correct
                    break
            for symmetry in _groups:
                if value.replace('-', '') == symmetry.name.replace('-', ''):
                    value = symmetry
                    break
        if not isinstance(value, Symmetry) and value is not None:
            raise ValueError(
                f"{value} must be of type {Symmetry}, the name of a valid point"
                " group as a string, or None."
            )
        else:
            self._symmetry = value

    def __repr__(self):
        if self.symmetry:
            symmetry_name = self.symmetry.name
        else:
            symmetry_name = self.symmetry  # Which should be None
        return (
            f"<name: {self.name}. symmetry: {symmetry_name}. color: "
            f"{self.color}>"
        )

    def deepcopy(self):
        """Return a deep copy using :py:func:`~copy.deepcopy` function."""
        return copy.deepcopy(self)


class PhaseList:
    """A list of phases in a crystallographic map.

    Each phase in the list must have a unique phase id as key.

    Attributes
    ----------
    size : int
        Number of phases in list.
    names : list of str
        List of phase names.
    symmetries : list of orix.quaternion.symmetry.Symmetry
        List of phase crystal symmetries.
    colors : list of tuple
        List of tuples with three entries, RGB, defining phase colors.
    phase_ids : list of int
        List of unique phase indices in a crystallographic map as imported.

    Methods
    -------
    deepcopy()
        Return a deep copy using :py:func:`~copy.deepcopy` function.
    """

    def __init__(
            self,
            phases=None,
            names=None,
            symmetries=None,
            colors=None,
            phase_ids=None,
    ):
        """
        Parameters
        ----------
        phases : orix.crystal_map.Phase, a list of orix.crystal_map.Phase\
                or a dictionary of orix.crystal_map.Phase
            A list or dict of phases or a single phase. The other arguments
            are ignored if this is passed.
        names : str or list of str
            Phase names.
        symmetries : str or list of str
            Point group symmetries.
        colors : str or list of str
            Phase colors.
        phase_ids : int, list of int or numpy.ndarray of int
            Phase IDs.
        """
        d = {}
        if isinstance(phases, list):
            try:
                if isinstance(next(iter(phases)), Phase):
                    d = dict(zip(np.arange(len(phases)), phases))
            except StopIteration:
                pass
        elif isinstance(phases, dict):
            try:
                if isinstance(next(iter(phases.values())), Phase):
                    d = phases
            except StopIteration:
                pass
        elif isinstance(phases, Phase):
            d = {0: phases}
        else:
            # Ensure possible single strings have iterables of length 1
            if isinstance(names, str):
                names = list((names,))
            if isinstance(symmetries, str):
                symmetries = list((symmetries,))
            if isinstance(colors, str):
                colors = list((colors,))

            # Get the maximum number of entries in the input lists (also
            # handling the case where some lists are None)
            max_entries = max([
                len(i) if i is not None else 0 for i in
                [names, symmetries, phase_ids]])

            if phase_ids is None:
                phase_ids = list(np.arange(max_entries))

            # Get first n entries in color list
            all_colors = list(islice(ALL_COLORS.keys(), max_entries))

            def get_entry_or_none(input_list, i):
                """Return list entry if it exists, else return None."""
                try:
                    return input_list[i]
                except (IndexError, TypeError):
                    return None

            # Create phase dictionary
            d = {}
            color_iter = 0
            phase_id_iter = 0
            for i in range(max_entries):
                name = get_entry_or_none(names, i)
                symmetry = get_entry_or_none(symmetries, i)

                # Always return a color (possibly not unique)
                try:
                    color = colors[i]
                except (IndexError, TypeError):
                    color = all_colors[color_iter]
                    color_iter += 1

                # Always return a unique phase_id_map
                try:
                    phase_id = phase_ids[i]
                except IndexError:
                    if phase_ids is not None:
                        phase_id = max(phase_ids) + phase_id_iter + 1
                    else:
                        phase_id = phase_id_iter
                    phase_id_iter += 1

                d[phase_id] = Phase(name=name, symmetry=symmetry, color=color)

        # Finally create dictionary of phases
        self._dict = OrderedDict(sorted(d.items()))

    @property
    def names(self):
        """Return a list of phase names in the list."""
        return [phase.name for _, phase in self]

    @property
    def symmetries(self):
        """Return a list of crystal symmetries of phases in the list."""
        return [phase.symmetry for _, phase in self]

    @property
    def colors(self):
        """Return a list of phase color names in the list."""
        return [phase.color for _, phase in self]

    @property
    def colors_rgb(self):
        """Return a list of phase color RGB values in the list."""
        return [phase.color_rgb for _, phase in self]

    @property
    def size(self):
        """Return number of phases in the list."""
        return len(self._dict.items())

    @property
    def phase_ids(self):
        """Return unique phase IDs in the list of phases."""
        return list(self._dict.keys())

    def __getitem__(self, key):
        """Return a PhaseList or a Phase object, depending on input.

        Examples
        --------
        A PhaseList object can be indexed in multiple ways.
        >>> pl = PhaseList(names=['a', 'b'], symmetries=['1', '3'])
        >>> pl
        Id  Name  Symmetry  Color
        0   a     1         tab:blue
        1   b     3         tab:orange

        Return a Phase object

        >>> pl[0]  # Index with a single phase id
        <name: a. symmetry: 1. color: tab:blue>
        >>> pl['b']  # Index with a phase name
        <name: b. symmetry: 3. color: tab:orange>

        Return a PhaseList object

        >>> pl[0:]  # Index with slices
        Id  Name  Symmetry  Color
        0   a     1         tab:blue
        1   b     3         tab:orange
        >>> pl['a', 'b']  # Index with a tuple of phase names
        Id  Name  Symmetry  Color
        0   a     1         tab:blue
        1   b     3         tab:orange
        >>> pl[0, 1]  # Index with a tuple of phase ids
        Id  Name  Symmetry  Color
        0   a     1         tab:blue
        1   b     3         tab:orange
        >>> pl[[0, 1]]  # Index with a list of phase_ids
        Id  Name  Symmetry  Color
        0   a     1         tab:blue
        1   b     3         tab:orange
        >>> pl[np.array([0, 1])]  # Index with a numpy.ndarray
        Id  Name  Symmetry  Color
        0   a     1         tab:blue
        1   b     3         tab:orange
        """

        # Make key iterable if it isn't already
        if (
                not isinstance(key, tuple)
                and not isinstance(key, slice)
                and not isinstance(key, list)
                and not isinstance(key, np.ndarray)
        ):
            key_iter = (key,)
        else:
            key_iter = key

        d = {}
        if (
                isinstance(key_iter, str)
                or (
                isinstance(key_iter, tuple) and isinstance(key_iter[0], str))
        ):
            for key_name in list(set(key_iter)):  # Use set to remove duplicates
                match = False
                for i, phase in self._dict.items():
                    if key_name == phase.name:
                        d[i] = phase
                        match = True
                if not match:
                    # Raises if any string in list of strings is not found
                    raise IndexError(
                        f"{key_name} is not among the available phases "
                        f"{self.names}."
                    )
        elif (
                isinstance(key_iter, int)
                or isinstance(key_iter, tuple)
                or isinstance(key_iter, list)
                or isinstance(key_iter, np.ndarray)
        ):
            for i in list(set(key_iter)):  # Use set to remove duplicates
                try:
                    d[i] = self._dict[i]
                except KeyError:
                    raise IndexError(
                        f"{i} is not among the available phase IDs "
                        f"{self.phase_ids}."
                    )
        elif isinstance(key_iter, slice):
            # Dicts cannot be sliced, hence this work-around
            id_arr = np.arange(max(self.phase_ids) + 1)
            sliced_arr = id_arr[key_iter]
            ids_in_slice = [i for i in sliced_arr if i in self.phase_ids]
            if ids_in_slice:
                d = {i: self._dict[i] for i in ids_in_slice}
            else:
                raise IndexError(
                    f"{key} is not valid for the available phase IDs "
                    f"{self.phase_ids}."
                )
        else:
            raise IndexError(f"{key} is not a valid indexing value.")

        # Return a Phase object if only one phase was asked for
        if isinstance(key, int) or isinstance(key, str):
            return [i for i in d.values()][0]
        else:
            return PhaseList(d)

    def __setitem__(self, key, value):
        """Add phase to list with a key (phase_id_map) and value (symmetry)."""
        if key not in self.names:
            # Make sure the new phase gets a new color
            color_new = None
            for color_name in ALL_COLORS.keys():
                if color_name not in self.colors:
                    color_new = color_name
                    break

            # Create new ID
            if self.phase_ids:
                new_phase_id = max(self.phase_ids) + 1
            else:
                new_phase_id = 0

            self._dict[new_phase_id] = Phase(
                name=key, symmetry=value, color=color_new)
        else:
            raise ValueError(
                f"{key} is already in the phase list {self.names}.")

    def __iter__(self):
        # Returning keys() and values() might confuse the user since the class
        # is called PhaseList. Could perhaps change class name to PhaseDict?
        # Called it PhaseList since MTEX calls it that...
        for phase_id, phase in self._dict.items():
            yield phase_id, phase

    def __repr__(self):
        # Ensure attributes set to None are treated OK
        names = ['None' if not i else i for i in self.names]
        symmetry_names = ['None' if not i else i.name for i in self.symmetries]

        # Determine column widths (allowing PhaseList to be empty)
        id_len = 2
        name_len = 4
        if names:
            name_len = max(max([len(i) for i in names]), name_len)
        sym_len = 8
        if symmetry_names:
            sym_len = max(max([len(i) for i in symmetry_names]), sym_len)
        col_len = 5
        if self.colors:
            col_len = max(max([len(i) for i in self.colors]), col_len)

        # Header
        representation = (
            "{:<{width}} ".format("Id", width=id_len)
            + "{:<{width}} ".format("Name", width=name_len)
            + "{:<{width}} ".format("Symmetry", width=sym_len)
            + "{:<{width}}\n".format("Color", width=col_len)
        )

        # Overview of each phase
        for i, phase_id in enumerate(self.phase_ids):
            representation += (
                    f"{phase_id:<{id_len}} "
                    + f"{names[i]:<{name_len}} "
                    + f"{symmetry_names[i]:<{sym_len}} "
                    + f"{self.colors[i]:<{col_len}}\n"
            )

        return representation

    def deepcopy(self):
        """Return a deep copy using :py:func:`~copy.deepcopy` function."""
        return copy.deepcopy(self)
