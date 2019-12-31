from .abstract_model import ModelMeta
from .storable_model import StorableModel
from .sharded_model import ShardedModel
from uengine.errors import MissingSubmodel, UnknownSubmodel, WrongSubmodel, InputDataError, IntegrityError


class SubmodelMeta(ModelMeta):

    @staticmethod
    def _get_collection(model_cls, name, bases, dct):
        # SubModels inherit their collections from parent classes.
        if hasattr(model_cls, "__collection__") and model_cls.__collection__:
            return model_cls.__collection__
        return None  # No autogeneration


class BaseSubmodelMixin:
    """
    Do not use this mixin directly. Subclass StorableSubmodel or
    ShardedSubmodel instead
    """

    __submodel__ = None
    __auxiliary_slots__ = ["__submodel__"]
    __fields__ = ["submodel"]
    __required_fields__ = ["submodel"]
    __submodel_loaders = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.is_new:
            if not self.__submodel__:
                raise IntegrityError(f"Attempted to create an object of abstract model {self.__class__.__name__}")
            if "submodel" in data:
                raise InputDataError("Attempt to override submodel for a new object")
            self.submodel = self.__submodel__
        else:
            if not self.submodel:
                raise MissingSubmodel(f"{self.__class__.__name__} has no submodel in the DB. Bug?")
            self._check_submodel()

    def _check_submodel(self):
        if self.submodel != self.__submodel__:
            raise WrongSubmodel(
                f"Attempted to load {self.submodel} as {self.__class__.__name__}. Correct submodel "
                f"would be {self.__submodel__}. Bug?"
            )

    def _validate(self):
        super()._validate()
        self._check_submodel()

    @classmethod
    def register_submodel(cls, name, constructor):
        if cls.__submodel__:
            raise IntegrityError("Attempted to register a submodel with another submodel")
        if not cls.__submodel_loaders:
            cls.__submodel_loaders = {}
        if name in cls.__submodel_loaders:
            raise IntegrityError(f"Submodel {name} is already registered")
        cls.__submodel_loaders[name] = constructor

    @classmethod
    def from_data(cls, **data):
        if "submodel" not in data:
            raise MissingSubmodel(f"{cls.__name__} has no submodel in the DB. Bug?")
        if not cls.__submodel_loaders:
            return cls(**data)
        submodel_name = data["submodel"]
        if submodel_name not in cls.__submodel_loaders:
            raise UnknownSubmodel(f"Submodel {submodel_name} is not registered with {cls.__name__}")
        return cls.__submodel_loaders[submodel_name](**data)

    @classmethod
    def _preprocess_query(cls, query):
        if not cls.__submodel__:
            return query
        processed = {"submodel": cls.__submodel__}
        processed.update(query)
        return processed


class StorableSubmodel(BaseSubmodelMixin, StorableModel, metaclass=SubmodelMeta):
    pass


class ShardedSubmodel(BaseSubmodelMixin, ShardedModel, metaclass=SubmodelMeta):
    pass
