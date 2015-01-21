import numpy
import theano
from theano import tensor
from numpy.testing import assert_allclose

from blocks.datasets import ContainerDataset
from blocks.main_loop import MainLoop
from blocks.extensions import TrainingExtension, FinishAfter
from blocks.extensions.monitoring import TrainingDataMonitoring
from blocks.algorithms import GradientDescent, SteepestDescent
from blocks.utils import shared_floatx

floatX = theano.config.floatX

def test_training_data_monitoring():
    weights = numpy.array([-1, 1], dtype=floatX)
    features = [numpy.array(f, dtype=floatX)
                for f in [[1, 2], [3, 4], [5, 6]]]
    targets = [(weights * f).sum() for f in features]
    n_batches = 3
    dataset = ContainerDataset(dict(features=features, targets=targets))

    x = tensor.vector('features')
    y = tensor.scalar('targets')
    W = shared_floatx([0, 0], name="W")
    cost = ((x * W).sum() - y) ** 2
    cost.name = 'cost'

    class TrueCostExtension(TrainingExtension):

        def before_batch(self, data):
            self.main_loop.log.current_row.true_cost = (
                ((W.get_value() * data["features"]).sum()
                 - data["targets"]) ** 2)

    main_loop = MainLoop(
        model=None, data_stream=dataset.get_default_stream(),
        algorithm=GradientDescent(cost=cost, params=[W],
                                  step_rule=SteepestDescent(0.001)),
        extensions=[
            FinishAfter(after_n_epochs=1),
            TrainingDataMonitoring([W, cost], "train1",
                                    after_every_batch=True),
            TrainingDataMonitoring([W, cost], "train2",
                                    after_every_epoch=True),
            TrueCostExtension()])

    main_loop.run()

    for i in range(n_batches):
        # The ground truth is written to the log before the batch is
        # processed, where as the extension writes after the batch is
        # processed. This is why the iteration numbers differs here.
        assert_allclose(main_loop.log[i].true_cost,
                        main_loop.log[i + 1].train1_cost)
    assert_allclose(
        main_loop.log[n_batches].train2_cost,
        sum([main_loop.log[i].true_cost for i in range(n_batches)]) / 3)
