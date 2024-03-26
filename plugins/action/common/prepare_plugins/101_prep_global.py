class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']
        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']
