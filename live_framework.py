

class LiveFramework:

    def __init__(self, configs: Dict):

        self.configs = configs
        self.model = None
        self.model_trained_at: int()

    def load_featuers
    def get_model(self):

        if 'model' in self.configs and self.configs['model'] is not None:

            model_trained_at = self.configs['model_trained_at']
            trained_model = self.configs['model']

    def train_model(self):

        # consider asserting that the model was not trained to recently

        raise NotImplementedError

