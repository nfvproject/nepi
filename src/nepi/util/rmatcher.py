#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

def match_tags(box, all_tags, exact_tags):
    """ returns True if box has required tags """
    tall = set(all_tags)
    texact = set(exact_tags)

    if texact and box.connections == texact:
        return True

    if tall and tall.issubset(box.connections):
        return True

    return False

def find_boxes(box, all_tags = None, exact_tags = None, max_depth = 1):
    """ Look for the connected boxes with the required tags, doing breath-first
    search, until max_depth ( max_depth = None will traverse the entire graph ).
    """
    if not all_tags and not exact_tags:
        msg = "No matching criteria for resources."
        raise RuntimeError(msg)

    queue = set()
    # enqueue (depth, box) 
    queue.add((0, box))
    
    traversed = set()
    traversed.add(box)

    depth = 0

    result = set()

    while len(q) > 0: 
        (depth, a) = queue.pop()
        if match_tags(a, all_tags, exact_tags):
            result.add(a)

        if not max_depth or depth <= max_depth:
            depth += 1
            for b in sorted(a.connections):
                if b not in traversed:
                    traversed.add(b)
                    queue.add((depth, b))
    
    return result
