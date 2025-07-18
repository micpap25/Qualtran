#  Copyright 2023 Google LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from functools import cached_property
from typing import Dict, List

import numpy as np
import quimb.tensor as qtn
from attrs import frozen

from qualtran import Bloq, BloqBuilder, ConnectionT, QAny, Signature
from qualtran.bloqs.bookkeeping import Join, Split
from qualtran.simulation.tensor import cbloq_to_quimb


@frozen
class TensorAdderSimple(Bloq):
    @cached_property
    def signature(self) -> 'Signature':
        return Signature.build(x=1)

    def my_tensors(
        self, incoming: Dict[str, 'ConnectionT'], outgoing: Dict[str, 'ConnectionT']
    ) -> List['qtn.Tensor']:
        assert list(incoming.keys()) == ['x']
        assert list(outgoing.keys()) == ['x']
        return [qtn.Tensor(data=np.eye(2), inds=[(incoming['x'], 0), (outgoing['x'], 0)])]


def test_cbloq_to_quimb():
    bb = BloqBuilder()
    x = bb.add_register('x', 1)
    x = bb.add(TensorAdderSimple(), x=x)
    x = bb.add(TensorAdderSimple(), x=x)
    x = bb.add(TensorAdderSimple(), x=x)
    x = bb.add(TensorAdderSimple(), x=x)
    cbloq = bb.finalize(x=x)

    tn = cbloq_to_quimb(cbloq)
    assert len(tn.tensors) == 4
    assert sorted(tn.outer_inds()) == [
        # reg_name, idx, j, side_str
        ('x', (), 0, 'l'),
        ('x', (), 0, 'r'),
    ]


def test_cbloq_to_quimb_with_no_ops_on_register():
    # Multiple registers with no operation on the target.
    signature = Signature.build(selection=2, target=1)
    bb, soqs = BloqBuilder().from_signature(signature=signature)
    selection, target = soqs['selection'], soqs['target']
    selection = bb.add(Split(QAny(2)), reg=selection)
    selection = bb.add(Join(QAny(2)), reg=selection)
    cbloq = bb.finalize(selection=selection, target=soqs['target'])
    np.testing.assert_allclose(cbloq.tensor_contract(), np.eye(2**3))

    # Single qubit with no operation acting on it.
    signature = Signature.build(target=1)
    bb, soqs = BloqBuilder().from_signature(signature=signature)
    cbloq = bb.finalize(**soqs)
    np.testing.assert_allclose(cbloq.tensor_contract(), np.eye(2))
