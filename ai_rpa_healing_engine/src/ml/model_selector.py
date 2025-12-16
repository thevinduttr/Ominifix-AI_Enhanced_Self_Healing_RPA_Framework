class ModelSelector:
    def __init__(self, model_path=None):
        self.model = None  # load later

    def predict_strategy(self, features):
        return "replace_locator"  # default placeholder
