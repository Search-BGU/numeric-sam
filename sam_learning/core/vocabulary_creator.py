import logging
from collections import defaultdict
from itertools import permutations
from typing import List, Tuple, Dict, Set, Union, Optional

from pddl_plus_parser.models import Predicate, PDDLObject, GroundedPredicate, PDDLType, Domain

from sam_learning.core import LearnerDomain


def choose_objects_subset(array: List[str], subset_size: int) -> List[Tuple[str]]:
    """Choose r items our of a list size n.

    :param array: the input list.
    :param subset_size: the size of the subset.
    :return: a list containing subsets of the original list.
    """
    return list(permutations(array, subset_size))


class VocabularyCreator:
    """Creates predicate vocabulary from a domain containing action signatures and predicate definitions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _validate_type_matching(self, grounded_signatures: Dict[str, PDDLType], predicate: Predicate) -> bool:
        """Validates that the types of the grounded signature match the types of the predicate signature.

        :param grounded_signatures: the grounded predicate signature.
        :param predicate: the lifted predicate.
        :return: whether the types match.
        """
        for object_name, predicate_parameter in zip(grounded_signatures, predicate.signature):
            parameter_type = predicate.signature[predicate_parameter]
            grounded_type = grounded_signatures[object_name]
            if not grounded_type.is_sub_type(parameter_type):
                self.logger.debug(f"The combination of objects - {grounded_signatures}"
                                  f" does not fit {predicate.name}'s signature")
                return False

        return True

    def create_vocabulary(self, domain: Union[LearnerDomain, Domain],
                          observed_objects: Dict[str, PDDLObject]) -> Dict[str, Set[GroundedPredicate]]:
        """Create a vocabulary of random combinations of the predicates parameters and objects.

        :param domain: the domain containing the predicates and the action signatures.
        :param observed_objects: the objects that were observed in the trajectory.
        :return: list containing all the predicates with the different combinations of parameters.
        """
        vocabulary = defaultdict(set)
        possible_objects = list(observed_objects.keys()) + list(domain.constants.keys())
        objects_and_consts = list(observed_objects.values()) + list(domain.constants.values())
        for predicate in domain.predicates.values():
            predicate_name = predicate.name
            signature_permutations = choose_objects_subset(possible_objects, len(predicate.signature))
            for signature_permutation in signature_permutations:
                grounded_signature = {object_name: objects_and_consts[possible_objects.index(object_name)].type
                                      for object_name in signature_permutation}
                if not self._validate_type_matching(grounded_signature, predicate):
                    continue

                grounded_predicate = GroundedPredicate(name=predicate_name, signature=predicate.signature,
                                                       object_mapping={parameter_name: object_name for
                                                                       object_name, parameter_name in
                                                                       zip(grounded_signature, predicate.signature)})
                vocabulary[predicate.untyped_representation].add(grounded_predicate)

        return vocabulary

    def create_lifted_vocabulary(self, domain: Union[LearnerDomain, Domain],
                                 possible_parameters: Dict[str, PDDLType],
                                 must_be_parameter: Optional[str] = None) -> Set[Predicate]:
        """Create a vocabulary of random combinations of parameters that match the predicates.

        :param domain: the domain containing the predicates and the action signatures.
        :param possible_parameters: the parameters to use to create the vocabulary from.
        :return: list containing all the predicates with the different combinations of parameters.
        """
        self.logger.debug(f"Creating predicates vocabulary from {possible_parameters}")
        vocabulary = set()
        possible_parameters_names = list(possible_parameters.keys()) + list(domain.constants.keys())
        parameter_types = list(possible_parameters.values()) + [const.type for const in domain.constants.values()]
        for predicate in domain.predicates.values():
            predicate_name = predicate.name
            signature_permutations = choose_objects_subset(possible_parameters_names, len(predicate.signature))
            for signature_permutation in signature_permutations:
                bounded_lifted_signature = {param_name: parameter_types[possible_parameters_names.index(param_name)]
                                            for param_name in signature_permutation}

                if not self._validate_type_matching(bounded_lifted_signature, predicate):
                    continue

                if must_be_parameter is not None and must_be_parameter not in bounded_lifted_signature:
                    continue

                grounded_predicate = Predicate(name=predicate_name, signature=bounded_lifted_signature)
                vocabulary.add(grounded_predicate)

        self.logger.debug(f"Created vocabulary of size {len(vocabulary)}")
        return vocabulary
