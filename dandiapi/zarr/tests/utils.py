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
    # This must be set on an intermediate class, it won't work on a final subclass
    _options_class = _PostgenerationAttributesFactoryOptions
