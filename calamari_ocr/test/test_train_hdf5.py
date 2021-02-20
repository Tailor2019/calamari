import os
import tempfile
import unittest

from tensorflow import keras
from tfaip.base.data.pipeline.processor.params import SequentialProcessorPipelineParams

from calamari_ocr.ocr.dataset.datareader.hdf5.reader import Hdf5
from calamari_ocr.ocr.dataset.imageprocessors import PrepareSampleProcessorParams
from calamari_ocr.ocr.scenario import CalamariScenario
from calamari_ocr.ocr.training.params import CalamariTrainOnlyGeneratorParams
from calamari_ocr.scripts.train import main

this_dir = os.path.dirname(os.path.realpath(__file__))


def make_test_scenario(with_validation=False, preload=True):
    class CalamariHDF5ScenarioTest(CalamariScenario):
        @classmethod
        def default_trainer_params(cls):
            p = super().default_trainer_params()
            train = Hdf5(
                files=[os.path.join(this_dir, "data", "uw3_50lines", "uw3-50lines.h5")],
                preload=preload,
            )
            if with_validation:
                p.gen.val = Hdf5(
                    files=[os.path.join(this_dir, "data", "uw3_50lines", "uw3-50lines.h5")],
                    preload=preload
                )
                p.gen.train = train
                p.gen.__post_init__()
            else:
                p.gen = CalamariTrainOnlyGeneratorParams(train=train)

            p.gen.setup.val.batch_size = 1
            p.gen.setup.val.num_processes = 1
            p.gen.setup.train.batch_size = 1
            p.gen.setup.train.num_processes = 1
            p.epochs = 1
            p.samples_per_epoch = 2
            p.scenario.data.pre_proc = SequentialProcessorPipelineParams(
                run_parallel=False,
                processors=[PrepareSampleProcessorParams()],
            )
            p.scenario.data.__post_init__()
            p.scenario.__post_init__()
            p.__post_init__()
            return p

    return CalamariHDF5ScenarioTest


class TestHDF5Train(unittest.TestCase):
    def tearDown(self) -> None:
        keras.backend.clear_session()

    def test_simple_train(self):
        trainer_params = make_test_scenario(with_validation=False).default_trainer_params()
        with tempfile.TemporaryDirectory() as d:
            trainer_params.checkpoint_dir = d
            main(trainer_params)

    def test_train_with_val(self):
        trainer_params = make_test_scenario(with_validation=True).default_trainer_params()
        with tempfile.TemporaryDirectory() as d:
            trainer_params.checkpoint_dir = d
            main(trainer_params)


class TestHDF5TrainNoPreload(unittest.TestCase):
    def tearDown(self) -> None:
        keras.backend.clear_session()

    def test_simple_train(self):
        trainer_params = make_test_scenario(with_validation=False, preload=False).default_trainer_params()
        with tempfile.TemporaryDirectory() as d:
            trainer_params.checkpoint_dir = d
            main(trainer_params)

    def test_train_with_val(self):
        trainer_params = make_test_scenario(with_validation=True, preload=False).default_trainer_params()
        with tempfile.TemporaryDirectory() as d:
            trainer_params.checkpoint_dir = d
            main(trainer_params)


if __name__ == "__main__":
    unittest.main()