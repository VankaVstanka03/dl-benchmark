import abc
import sys
import importlib
import ast
import os
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils import Reader  # noqa: E402


class NNCFModelReader(Reader):
    def __init__(self, log):
        super().__init__(log)

    @staticmethod
    def get_reader(framework, log):
        if framework.lower() == 'tensorflow':
            return NNCFModelReaderTensorFLowFormat(log)
        elif framework.lower() == 'onnx':
            return NNCFModelReaderONNXFormat(log)
        elif framework.lower() == 'openvino':
            return NNCFModelReaderOpenVINOFormat(log)

    def _get_arguments(self):
        self._log.info('Parsing model arguments.')
        self.model_name = self.args['ModelName']
        self.model_path = self.args['ModelPath']
        self.model_params = self.args['WeightsPath']
        self.input_name = self.args['InputName']
        self.output_name = self.args['OutputName']
        self.input_shape = ast.literal_eval(self.args['InputShape'])
        self.device = self.args['Device']
        self.framework = self.args['Framework']
        self._read_model()

    def save_model(self, quant_model, output_directory):
        if output_directory is None:
            output_directory = os.getcwd()

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        self._log.info(f'Saving model to {output_directory}')
        self._save_model(quant_model, output_directory)

    @abc.abstractmethod
    def _read_model(self):
        pass

    @abc.abstractmethod
    def _save_model(self, quant_model, output_directory):
        pass


class NNCFModelReaderTensorFLowFormat(NNCFModelReader):
    def __init__(self, log):
        super().__init__(log)
        self.tf = importlib.import_module('tensorflow')
    
    def _read_model(self):
        self.model = self.tf.keras.models.load_model(Path(self.model_path))
    
    def _save_model(self, quant_model, output_directory):
        self.tf.keras.saving.save_model(quant_model, f'{output_directory}/probe_model', save_format='tf')


class NNCFModelReaderONNXFormat(NNCFModelReader):
    def __init__(self, log):
        super().__init__(log)
        self.onnx = importlib.import_module('onnx')

    def _read_model(self):
        self.model = self.onnx.load(self.model_path)

    def _save_model(self, quant_model, output_directory):
        self.onnx.save(quant_model, f'{output_directory}/{self.model_name}.onnx')


class NNCFModelReaderOpenVINOFormat(NNCFModelReader):
    def __init__(self, log):
        super().__init__(log)
        self.ov = importlib.import_module('openvino')
    
    def _read_model(self):
        core = self.ov.Core()
        self.model = core.read_model(self.model_path)

    def _save_model(self, quant_model, output_directory):
        self.ov.runtime.save_model(quant_model, f'{output_directory}/{self.model_name}.xml')
