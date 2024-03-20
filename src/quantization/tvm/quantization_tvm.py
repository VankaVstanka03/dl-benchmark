import argparse
import sys
import traceback
from pathlib import Path
from parameters import TVMModelReader, TVMQuantParamReader, TVMQuantizationProcess
sys.path.append(str(Path(__file__).resolve().parents[3]))
from src.utils.logger_conf import configure_logger  # noqa: E402
from src.quantization.utils import DatasetReader, ConfigParser  # noqa: E402

log = configure_logger()


def cli_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config',
                        help='Path to xml config.',
                        type=str,
                        required=True,
                        dest='config')
    args = parser.parse_args()
    return args


def iter_log(model_reader, data_reader, quant_params):
    log.info(f'Quantization config:\n\n\t'
             f'Model:\n\t\t'
             f'Path to json: {model_reader.model_path}\n\t\t'
             f'Path to params: {model_reader.model_params}\n\t'
             f'Dataset:\n\t\t'
             f'Name: {data_reader.dataset_name}\n\t\t'
             f'Path to folder: {data_reader.dataset_path}\n\t\t'
             f'Number of images: {data_reader.max}\n\t'
             f'Quantization parameters:\n\t\t'
             f'Calibration mode: {quant_params.calib_mode}\n\t\t'
             f'Weights scale: {quant_params.weights_scale}\n\t\t')


def main():
    args = cli_argument_parser()
    try:
        parser = ConfigParser(args.config)
        model_reader = TVMModelReader(log)
        data_reader = DatasetReader(log)
        quant_params = TVMQuantParamReader(log)
        proc = TVMQuantizationProcess(log, model_reader, data_reader, quant_params)

        log.info('Parsing xml config')
        config = parser.parse()
        for quant_iter in config:
            try:
                model_reader.add_arguments(quant_iter[0]['Model'])
                data_reader.add_arguments(quant_iter[1]['Dataset'])
                quant_params.add_arguments(quant_iter[2]['QuantizationParameters'])
                iter_log(model_reader, data_reader, quant_params)
                proc.quantization_tvm()
                proc.save_quant_model()
            except Exception:
                log.error(traceback.format_exc())
    except Exception:
        log.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main() or 0)
