from __future__ import annotations

import factory


class _PostgenerationAttributesFactoryOptions(factory.base.FactoryOptions):
    def use_postgeneration_results(self, step, instance, results):
        self.factory._after_postgeneration(
            instance,
            create=step.builder.strategy == factory.CREATE_STRATEGY,
            results=results,
            attributes=step.attributes,
        )


class PostgenerationAttributesFactory(factory.Factory):
    """
    A Factory that supplies `_after_postgeneration` with access to all input attributes.

    In particular, this allows `_after_postgeneration` to access `Params`, which it otherwise
    wouldn't have access to.

    See:
    https://github.com/FactoryBoy/factory_boy/issues/544
    https://github.com/FactoryBoy/factory_boy/issues/936
    """

    # This must be set on an intermediate class, it won't work on a final subclass
    _options_class = _PostgenerationAttributesFactoryOptions
