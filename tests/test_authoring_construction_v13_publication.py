"""ACC 1.3 authority publication tests; no runtime construction conformance claim."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from adr_kit.core import semantic_core_capabilities
from adr_kit.semantic_contract import (
    get_semantic_contract,
    load_semantic_resource,
    list_semantic_contracts,
    verify_semantic_contract,
    validate_semantic_resource_closure,
    calculate_semantic_contract_fingerprint,
)
from scripts import qualify_acc13_publication as publication

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "contracts/authoring-construction/v1.3"
ASSETS = ROOT / "contracts/semantic-contract/v1.0"
PACKAGE = ROOT / "src/adr_kit/semantic_contract/v1_0"
SCF = "scf:v1:sha256:e809df8b4c13da7db8afd5513af31329222b488fcbd1590d1a25246aaf64f96a"
UUID = "01900000-0000-7000-8000-000000000002"
HISTORICAL_GIT_BLOBS: dict[str, str] = {
    "contracts/architecture-interpretation/v1.1/contract.json": "a2686672169c7d8b4abea313f2871aea222bab0a",
    "contracts/architecture-interpretation/v1.1/resources/conformance.json": "3d544df0eb35148725f3f1231985068f313f42c9",
    "contracts/architecture-interpretation/v1.1/resources/legacy-compatibility.json": "20dab4078340a553f943028ff316f2c041fb9f85",
    "contracts/architecture-interpretation/v1.1/resources/rules.json": "a8bf737bc500dcda62ae50ea35e70fca9959c3ab",
    "contracts/architecture-interpretation/v1.1/resources/source-decoding-1.7.json": "b37b8c8dd552c5b386789d16f18e9b9368bfee25",
    "contracts/architecture-interpretation/v1.1/resources/source-mapping-1.7-to-2.4.json": "ffabe9db796812ca0ad2d5db5ceb6aa56949e3ac",
    "contracts/architecture-interpretation/v1.1/schema.json": "291828bb91b7d6e3c5810002bf15b087c19e1916",
    "contracts/architecture-interpretation/v1.2/contract.json": "e297a2fcbe07ba47cebcbc873d11b82249004dc5",
    "contracts/architecture-interpretation/v1.2/resources/conformance.json": "35b6d3cbeffa942e8cec7c1348d6aa643a55f5f4",
    "contracts/architecture-interpretation/v1.2/resources/conformance.schema.json": "c92e33564d658ad32e10842190aa86ac9ea241b6",
    "contracts/architecture-interpretation/v1.2/resources/detached-context.json": "02a9714f20fe663129ed0be82beef34f0d70bd62",
    "contracts/architecture-interpretation/v1.2/resources/field-dispositions-1.7-to-2.4.json": "16d64c3fa69159225c812c175c29cfc79f1cc8e8",
    "contracts/architecture-interpretation/v1.2/resources/field-dispositions.schema.json": "7463f6f1f7240340573101a712a970882df8b010",
    "contracts/architecture-interpretation/v1.2/resources/legacy-compatibility.json": "b8425ce9daedf65f929683c0a4dfa2c550b649b7",
    "contracts/architecture-interpretation/v1.2/resources/rules.json": "e111b553d684101772dd23948270400757224ccf",
    "contracts/architecture-interpretation/v1.2/resources/source-decoding-1.7.json": "23df3eda244ded4cd75982fbb54ac33b541768dd",
    "contracts/architecture-interpretation/v1.2/resources/source-mapping-1.7-to-2.4.json": "6085e4a7e60e867b4171d05652a935730f53f6f0",
    "contracts/architecture-interpretation/v1.2/schema.json": "6de80960db1ad3f6cdc6c74c9f0ceddd70938910",
    "contracts/architecture-interpretation/v1.3/contract.json": "68621fa69255cefda6780ab2b7ee4edcd96d8aca",
    "contracts/architecture-interpretation/v1.3/resources/conformance.json": "5b73625e351e1c2a3be7b6a8e845128238872b7c",
    "contracts/architecture-interpretation/v1.3/resources/conformance.schema.json": "373884821668639beec7567ebbfeeb98395dd6f6",
    "contracts/architecture-interpretation/v1.3/resources/contextual-facts.json": "52fb92511715b4761c5908b8f1b60a55a642eb46",
    "contracts/architecture-interpretation/v1.3/resources/contextual-facts.schema.json": "4078c232d9cc86e3075308037c64299abcc0fd06",
    "contracts/architecture-interpretation/v1.3/resources/detached-context.json": "256614a2b48b4ba373244aa31afb59bb879288d7",
    "contracts/architecture-interpretation/v1.3/resources/field-dispositions-1.7-to-2.5.json": "50826ad1f5eaeac99b8cfe6f3247d20bc55b5414",
    "contracts/architecture-interpretation/v1.3/resources/field-dispositions.schema.json": "335aebbcda9a961864b8ee4411aed9216838be9d",
    "contracts/architecture-interpretation/v1.3/resources/lifecycle-ownership.json": "f685c1aafb394054b5401091e7f8cb27f339ed8c",
    "contracts/architecture-interpretation/v1.3/resources/lifecycle-ownership.schema.json": "bb3315d5e3b107bdd71943ba25aea4f5401f9833",
    "contracts/architecture-interpretation/v1.3/resources/lifecycle-provenance.schema.json": "6eb602a1048a1bcd0dd1f3f3a708d0247d5074d7",
    "contracts/architecture-interpretation/v1.3/resources/rules.json": "e0f8410c671f4c329bb1c921c859092b6daac918",
    "contracts/architecture-interpretation/v1.3/resources/source-mapping-1.7-to-2.5.json": "a5112f12b4e7eceec0834200c2497d1a82403096",
    "contracts/architecture-interpretation/v1.3/schema.json": "d74d7f1c8862b48076d27accb07b513415792d54",
    "contracts/architecture-ir/architecture-ir.schema.json": "a2dc34087f92f0be8620b6fb65420bbd6aed229e",
    "contracts/authoring-construction/v1.0/contract.json": "b00fd399e1870b9577f8f7ec54dfc67f66196069",
    "contracts/authoring-construction/v1.0/resources/conformance.json": "ea0cd027cf5222695463905246b06ba9e3cfcebe",
    "contracts/authoring-construction/v1.0/resources/rules.json": "c4e877be8e1b17ff18461b5eacf241d7235d72d7",
    "contracts/authoring-construction/v1.0/schema.json": "17eb8440264f36ee00dae37e0c9ab5cdc0953328",
    "contracts/authoring-construction/v1.1/contract.json": "14981aefe18f9780152f0f96348e29e00a2f8cab",
    "contracts/authoring-construction/v1.1/resources/compatibility.json": "d50a9cf1187bd57a0ab43801bf9104d4bb29a87a",
    "contracts/authoring-construction/v1.1/resources/conformance.json": "7a2615ba5f9fd776c26bd7cbf17cd098011ab334",
    "contracts/authoring-construction/v1.1/resources/conformance.schema.json": "0028f3e2fa6f7b44a3147f7e4b7afac275857a17",
    "contracts/authoring-construction/v1.1/resources/ledger.schema.json": "4e14a67d12abd8e1440caf6ed9d49b411804a3cc",
    "contracts/authoring-construction/v1.1/resources/rules.json": "5b58d44bbf946df810eaa55fe84b09345fe4e977",
    "contracts/authoring-construction/v1.1/schema.json": "9cfc45094ec484e9dad5f2dbe38c2ca3c1bbd94d",
    "contracts/authoring-construction/v1.2/contract.json": "1918ad7eb7bf27ef2de187dc0215f6f399f3dc2b",
    "contracts/authoring-construction/v1.2/resources/compatibility.json": "8548cc25585e68dc557ccfa14c7617c1b10ae64c",
    "contracts/authoring-construction/v1.2/resources/composition-bindings.json": "7c2efa4107bf8f3d4009d5957168e7bdf95a1fd4",
    "contracts/authoring-construction/v1.2/resources/composition-bindings.schema.json": "b32c8db7a49ff32c5858d2ceffb1a1fc9265531e",
    "contracts/authoring-construction/v1.2/resources/conformance.json": "a2c9d403eb6717be9efd71475d3079dae9737286",
    "contracts/authoring-construction/v1.2/resources/conformance.schema.json": "e3ab956b30b055840f3c5048eebb73532d79d0f3",
    "contracts/authoring-construction/v1.2/resources/rules.json": "26f05bc8339c2ef00c3ee441c90aa37d41aa8dc1",
    "contracts/authoring-construction/v1.2/schema.json": "b731adaaa83d896db318964965bb1de10f6eb0d8",
    "contracts/authoring-domain/v1.0/contract.json": "b7af87f37338892c53a0fa629d41c9f7a69f4c7d",
    "contracts/authoring-domain/v1.0/schema.json": "7a89cd53441f3bee67b18279d37cb7f2e868a529",
    "contracts/authoring-domain/v1.1/contract.json": "141bb3eef837651a6cbe7ba48b0b57c4bac46cd5",
    "contracts/authoring-domain/v1.1/schema.json": "f34a32283010be36b6bed5f38b3a05df65b521e9",
    "contracts/compatibility/cli-behavior.json": "93f761392270bc52efe3ed1352a3802980964288",
    "contracts/compatibility/cli-surface.json": "fb96ec892889052145cd78d1e8e36b28a6fcf4be",
    "contracts/compatibility/host-capabilities.json": "c1f0c7c9d1bede96b1645141a00da63f3e37a0d3",
    "contracts/compatibility/python-capabilities.json": "76de2f99e68f9f78b07eecbc16ae4de84d404832",
    "contracts/compatibility/python-surface.json": "8c6e4b4b5abf376c473df9cb0dabdcb62f0f5c5c",
    "contracts/compatibility/typescript-surface.json": "9413b9cbb3e6a59a81bec43ace5b9bf9cb24e1cd",
    "contracts/conformance/consumer-binding-v1/authoring-discovery/authoring-discovery-v1.json": "38bc039ed120293345b5df13386b16785421b34f",
    "contracts/conformance/consumer-binding-v1/embodiment-linkage/evidence-v15.json": "a7d937cb688ab5a882c15b5a6d55da79573e57a2",
    "contracts/conformance/consumer-binding-v1/embodiment-linkage/evidence-v16-enforces-inferred.json": "e83947ddfd5f55ed87757f4356bad87c811ca68c",
    "contracts/conformance/consumer-binding-v1/embodiment-linkage/evidence-v16.json": "da8214a7c2751c9a621624cbc73227f2200d488c",
    "contracts/conformance/consumer-binding-v1/manifest.json": "f9e166429eb278d8f30c11a2e7570ef7a3760cc1",
    "contracts/conformance/consumer-binding-v1/relationships/canonical-and-compatibility.json": "f4cdbb72ac55bc16fdcc3adb5f48886b462bc0d1",
    "contracts/conformance/consumer-binding-v1/repository/model-v21.json": "b85feb5e4f4e1c8a15ecfda134544ab0661bf1cd",
    "contracts/conformance/consumer-binding-v1/repository/unsupported-model.json": "35319caa56a4956a70d202151fc8c9844052185b",
    "contracts/conformance/consumer-binding-v1/semantic-extensions/core-extension-invalid.json": "17240dd77d5302edf5c10a70bbe8a0fd543dc949",
    "contracts/conformance/consumer-binding-v1/semantic-extensions/qualified-unknown.json": "8ad35b926a1026ff724aecaa0b6b33cbb1fccb44",
    "contracts/conformance/consumer-binding-v1/unresolved/unresolved-first-class.json": "e89e1eea403951ac337d3ab7d9538544b6340f9e",
    "contracts/custom-entity/registries/adrkit/registry.json": "e720d426df89294aa87dae3acb3a0ed935030546",
    "contracts/custom-entity/v1.0/contract.json": "9a55aedcad61a7342ac626567302bc311b9b6adf",
    "contracts/custom-entity/v1.0/schema.json": "5ae8eddcd5d1ca887fe52a92855ebb4ed390201c",
    "contracts/custom-entity/v1.0/vectors/contract-fingerprint.json": "040724768316afd3c8899582f99647cf6ed7d1cd",
    "contracts/design-journal-promotion-contract/v0.1/conformance/01-valid-promotable-pre-lock.json": "4950e479931c55f298a4574b56723ad3cfb5fdce",
    "contracts/design-journal-promotion-contract/v0.1/conformance/02-valid-locked.json": "b5b80ceb411533a77bcd038f1e1e0789a6abbb3d",
    "contracts/design-journal-promotion-contract/v0.1/conformance/03-non-promotable.json": "b6487f4343e0adc17d52db567568977c3448cf4a",
    "contracts/design-journal-promotion-contract/v0.1/conformance/04-unresolved-outcome-ref.json": "a4497755cfddef0e01c913aed59174f612c5286a",
    "contracts/design-journal-promotion-contract/v0.1/conformance/05-duplicate-outcome-id.json": "69af3a86364fe9533466667f60b52457a8cadcc9",
    "contracts/design-journal-promotion-contract/v0.1/conformance/06-unmapped-promotion-required.json": "e5c153b5435651f14cfd253cc58186a46c2151c5",
    "contracts/design-journal-promotion-contract/v0.1/conformance/07-blocker-with-mechanical-true.json": "c837a75e8b3a58a0c7323c67099972efb0bb0024",
    "contracts/design-journal-promotion-contract/v0.1/conformance/08-unbound-payload-ref.json": "e30becd3958f5cce3155e02811f6409014c9d382",
    "contracts/design-journal-promotion-contract/v0.1/conformance/09-schema-binding-mismatch.json": "19f8d1a045644c657c2bb1123b8dc01bc842a154",
    "contracts/design-journal-promotion-contract/v0.1/conformance/10-baseline-provider-mismatch.json": "48e27e5d78e47ebaddc65f07179628b117fc2241",
    "contracts/design-journal-promotion-contract/v0.1/conformance/11-statement-change-invalidates.json": "a242cb19f8b7e44377bb1248f9d5af9bb917cc68",
    "contracts/design-journal-promotion-contract/v0.1/conformance/12-mutation-change-invalidates.json": "29493ce3e31ff5e22947c1af027452d5e3d7f371",
    "contracts/design-journal-promotion-contract/v0.1/conformance/13-multi-provider-unsupported.json": "03246daa949b8ae57b8556c8caf42a96de0e7df4",
    "contracts/design-journal-promotion-contract/v0.1/conformance/14-class-d-retry.json": "3aaf45451f3806fa456cd5dc6e14592d3567ecd1",
    "contracts/design-journal-promotion-contract/v0.1/schema.json": "da758836d501c1c2971943761a8ea948983d89c2",
    "contracts/design-journal/v0.1/schema.json": "0614a3921dea0712b5013796358869dae8745339",
    "contracts/semantic-contract/v1.0/catalog/semantic-contract-catalog-1.0.json": "4659545c9b93af7b7e72d93a404ad8e4930f5bb5",
    "contracts/semantic-contract/v1.0/current/semantic-contract-current-1.0.json": "4383eb0bf08795823bed583b4169eb0a2bf4e677",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.1.json": "71b7248658c387a7bf23ac3cc51317d4d696b9b6",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.2.json": "e297a2fcbe07ba47cebcbc873d11b82249004dc5",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.3.json": "68621fa69255cefda6780ab2b7ee4edcd96d8aca",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation.json": "9f044344c33fc3479549d5558675451d48574a75",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.0.json": "b00fd399e1870b9577f8f7ec54dfc67f66196069",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.1.json": "14981aefe18f9780152f0f96348e29e00a2f8cab",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.2.json": "1918ad7eb7bf27ef2de187dc0215f6f399f3dc2b",
    "contracts/semantic-contract/v1.0/definitions/normalized-model-2.4.json": "a0559a5bda8fd65b90b5b0d9b79949c745df464c",
    "contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json": "cfcd46fa7aefced4213274fc26969dca1b05983c",
    "contracts/semantic-contract/v1.0/definitions/normalized-model.json": "6b49bd32ff0fd91198a531654c911da1e9f4e925",
    "contracts/semantic-contract/v1.0/definitions/normative-semantics-1.0.json": "2ae295dee7b7f6a9d353839ec8b019798a670464",
    "contracts/semantic-contract/v1.0/definitions/normative-semantics.json": "2ae295dee7b7f6a9d353839ec8b019798a670464",
    "contracts/semantic-contract/v1.0/policy/semantic-contract-policy-1.0.json": "363e8535ddc8f5fdffcc7f375ebb9b13bf40f562",
    "contracts/semantic-contract/v1.0/profiles/architecture-materialization-1.0.json": "e0ff9a7b0f2a82040c311b1e8fa1df806db309a8",
    "contracts/semantic-contract/v1.0/profiles/architecture-materialization-1.1.json": "5a5647ee5b1157da995d1e2bf70d5f30d471137b",
    "contracts/semantic-contract/v1.0/qualifications/architecture-materialization-1.0.json": "3e7921f14ff09dcc360beb8c02d36e4a7f6aa115",
    "contracts/semantic-contract/v1.0/qualifications/architecture-materialization-1.1.json": "65e130f71eb9d5f80757146e8733ebe88b641cee",
    "contracts/semantic-contract/v1.0/resource-manifest-entry.schema.json": "217cd4b79e7f780f0042b1a060b8b725c8498f47",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-conformance.json": "3d544df0eb35148725f3f1231985068f313f42c9",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-legacy-compatibility.json": "20dab4078340a553f943028ff316f2c041fb9f85",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-rules.json": "a8bf737bc500dcda62ae50ea35e70fca9959c3ab",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-source-decoding-1.7.json": "b37b8c8dd552c5b386789d16f18e9b9368bfee25",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-source-mapping-1.7-to-2.4.json": "ffabe9db796812ca0ad2d5db5ceb6aa56949e3ac",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-conformance.json": "35b6d3cbeffa942e8cec7c1348d6aa643a55f5f4",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-conformance.schema.json": "c92e33564d658ad32e10842190aa86ac9ea241b6",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-contract.json": "e297a2fcbe07ba47cebcbc873d11b82249004dc5",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-detached-context.json": "02a9714f20fe663129ed0be82beef34f0d70bd62",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-field-dispositions-1.7-to-2.4.json": "16d64c3fa69159225c812c175c29cfc79f1cc8e8",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-field-dispositions.schema.json": "7463f6f1f7240340573101a712a970882df8b010",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-legacy-compatibility.json": "b8425ce9daedf65f929683c0a4dfa2c550b649b7",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-rules.json": "e111b553d684101772dd23948270400757224ccf",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-source-decoding-1.7.json": "23df3eda244ded4cd75982fbb54ac33b541768dd",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-source-mapping-1.7-to-2.4.json": "6085e4a7e60e867b4171d05652a935730f53f6f0",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-conformance.json": "5b73625e351e1c2a3be7b6a8e845128238872b7c",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-conformance.schema.json": "373884821668639beec7567ebbfeeb98395dd6f6",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-contextual-facts.json": "52fb92511715b4761c5908b8f1b60a55a642eb46",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-contextual-facts.schema.json": "4078c232d9cc86e3075308037c64299abcc0fd06",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-detached-context.json": "256614a2b48b4ba373244aa31afb59bb879288d7",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-field-dispositions-1.7-to-2.5.json": "50826ad1f5eaeac99b8cfe6f3247d20bc55b5414",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-field-dispositions.schema.json": "335aebbcda9a961864b8ee4411aed9216838be9d",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-lifecycle-ownership.json": "f685c1aafb394054b5401091e7f8cb27f339ed8c",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-lifecycle-ownership.schema.json": "bb3315d5e3b107bdd71943ba25aea4f5401f9833",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-lifecycle-provenance.schema.json": "6eb602a1048a1bcd0dd1f3f3a708d0247d5074d7",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-rules.json": "e0f8410c671f4c329bb1c921c859092b6daac918",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-source-mapping-1.7-to-2.5.json": "a5112f12b4e7eceec0834200c2497d1a82403096",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-conformance.json": "5d08a88e11400b7999282c0e80213b7554098794",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-rules.json": "838b93f10b0a53d1ec143fc549df537bac2f2615",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-source-decoding-1.5.json": "70494489a90c0575be39d578c9a02eb393a77e7a",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-source-decoding-1.6.json": "514f306d1f4e232f2e78119a4678ceeb646cb89a",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-source-mapping-1.5-to-2.3.json": "90bfc54232432de2fef5d4a86f778491e1a37b5c",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-source-mapping-1.6-to-2.3.json": "d6d1d6bae242d4de7a30e82e6094fabc4654914f",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-common.schema.json": "8742fc72bec6deb19fa23bb9aba24abbc55bba6a",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-logical.schema.json": "2e8970ea00e9d17b0f72dd3f39f4552b42374258",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-physical-base.schema.json": "a6d1d632832df1e834fe31209cc9bd365a3db387",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-physical-component.schema.json": "4d3840293e9fb4422da29f13dddee59f6053e54a",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-physical-system.schema.json": "515337837f872e421ebe2cb012b6ac152e452457",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-types.schema.json": "20a7e04e978d6aacf6ddbcce26cf5788726d6d91",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-common.schema.json": "c8d403e54b155144f337388f305697ebdde6b603",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-logical.schema.json": "a68a4bad72d091d714d1c0459df1b7a1c4f82e4c",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-physical-base.schema.json": "6f747066e5dd64a015072d3908fa0baf86865213",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-physical-component.schema.json": "e293c45dcbf7a7a38df0fd6d8b7f4a2dc3f2fa3e",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-physical-system.schema.json": "985a4b2f0eec608a64b245cbd22704ce22c078a6",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-types.schema.json": "4825ec219d528894dcc1d9446552a1db880c084b",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-common.schema.json": "ba8e11a19b7fb329dcd8c3a2332f20ef75ce87b7",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-logical.schema.json": "5adc9ff1064faa6c30eb47fcb7544f74d88d019d",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-physical-base.schema.json": "9f67d1e4feeb0dfb18f4c21a2bb2035b8c6343e0",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-physical-component.schema.json": "ff224da9fb83a92133731acf0a05130bf207c9b4",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-physical-system.schema.json": "efb87b2c4ed5ce4a8c8215df993c1125a0da5f25",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-types.schema.json": "65b510d52d2036d3807ec7725600f163ca6543fb",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.0-conformance.json": "ea0cd027cf5222695463905246b06ba9e3cfcebe",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.0-contract.json": "b00fd399e1870b9577f8f7ec54dfc67f66196069",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.0-rules.json": "c4e877be8e1b17ff18461b5eacf241d7235d72d7",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-compatibility.json": "d50a9cf1187bd57a0ab43801bf9104d4bb29a87a",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-conformance.json": "7a2615ba5f9fd776c26bd7cbf17cd098011ab334",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-conformance.schema.json": "0028f3e2fa6f7b44a3147f7e4b7afac275857a17",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-contract.json": "14981aefe18f9780152f0f96348e29e00a2f8cab",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-ledger.schema.json": "4e14a67d12abd8e1440caf6ed9d49b411804a3cc",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-rules.json": "5b58d44bbf946df810eaa55fe84b09345fe4e977",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-schema.json": "9cfc45094ec484e9dad5f2dbe38c2ca3c1bbd94d",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-compatibility.json": "8548cc25585e68dc557ccfa14c7617c1b10ae64c",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-composition-bindings.json": "7c2efa4107bf8f3d4009d5957168e7bdf95a1fd4",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-composition-bindings.schema.json": "b32c8db7a49ff32c5858d2ceffb1a1fc9265531e",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-conformance.json": "a2c9d403eb6717be9efd71475d3079dae9737286",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-conformance.schema.json": "e3ab956b30b055840f3c5048eebb73532d79d0f3",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-rules.json": "26f05bc8339c2ef00c3ee441c90aa37d41aa8dc1",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-schema.json": "b731adaaa83d896db318964965bb1de10f6eb0d8",
    "contracts/semantic-contract/v1.0/resources/authoring-domain-1.1-contract.json": "141bb3eef837651a6cbe7ba48b0b57c4bac46cd5",
    "contracts/semantic-contract/v1.0/resources/authoring-domain-1.1-schema.json": "f34a32283010be36b6bed5f38b3a05df65b521e9",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-conformance.json": "040724768316afd3c8899582f99647cf6ed7d1cd",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-contract.json": "9a55aedcad61a7342ac626567302bc311b9b6adf",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-schema.json": "5ae8eddcd5d1ca887fe52a92855ebb4ed390201c",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-conformance.json": "56819288be8a0fb47d29930acb702a8d8d59ec93",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-architecture-model.schema.json": "c5caf6b3f008b9d32dacaeed9d251e2978773004",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-entity-registry.schema.json": "c3ba0f7648127dc874bf6887bf59dc33e430bcab",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-entity.schema.json": "cc5bd2bac84978bd3a82fa99b480767df21d8926",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-relationship-record.schema.json": "e3e3ebe44c510f83e8b819fd2b07efbf8aa8a24d",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-relationship-registry.schema.json": "f48a86f505c95cb4b426f2183d68f0273e4da0e2",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-unresolved-registry.schema.json": "a53140c599338ae13f285c29a6ac18315e204958",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-conformance.json": "47ec0af3b6c59774aacc85ed6ef4eddbe2a63b3a",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-architecture-model.schema.json": "51ab6b0fc9538696946a7bd617600898fda16e4b",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-entity-registry.schema.json": "36cfa43d043f52a6e5f716958f33925580f92cf3",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-entity.schema.json": "392c89dc7cfd91dfa2e93ba08448cac9b9d63c9c",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-relationship-record.schema.json": "1fe37c1195387bcd7e8eeb791f6dca0df3295588",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-relationship-registry.schema.json": "8d0c87b1d460e1c3d15f72693eca74278331718f",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-unresolved-registry.schema.json": "3a799c04c6c3244034422d380711e862f1bc0146",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-conformance.json": "a8dc61f59e2e78f24ed1bcaea2d46fb82260c988",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-normalized-architecture-model.schema.json": "3636ada2596ceef1346eec2139e71e41d2fb8995",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-normalized-entity-registry.schema.json": "5423e7691ef7f164520700a0f000d150b8e48434",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-normalized-entity.schema.json": "ba5695c3825ff68c8e9e25105c333bc9d61ba75e",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-relationship-record.schema.json": "17a20848fc6e2c6978b9ef3f766174a8d1a390d9",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-relationship-registry.schema.json": "cd50b77e12b260630482cb372250a1aeae6d8a3b",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-unresolved-registry.schema.json": "98df9d01073e0ec0d9e51db803f3198bb340b82f",
    "contracts/semantic-contract/v1.0/resources/normative-semantics-conformance.json": "d71f955a91cf0c3dbb9349560dd55ff4819bbdac",
    "contracts/semantic-contract/v1.0/resources/normative-semantics-definition.json": "03ccd326feebb77b3b28c486c93fdf7e2a9c7e46",
    "contracts/semantic-contract/v1.0/semantic-contract-assembly-request.schema.json": "993460bf51d68f694749b07c1b97303d163db861",
    "contracts/semantic-contract/v1.0/semantic-contract-assembly-result.schema.json": "36ece4eafd877f5ac70788e22f7829de43bc16b6",
    "contracts/semantic-contract/v1.0/semantic-contract-catalog.schema.json": "b2fd72609c2e31a5cb43b54f5d9fcc36364084ef",
    "contracts/semantic-contract/v1.0/semantic-contract-corpus-validation-request.schema.json": "5aa34bd05786d453c9d3b6ec3533841244285fd2",
    "contracts/semantic-contract/v1.0/semantic-contract-corpus-validation-result.schema.json": "0ffbaa509311db79c8849aab33a2075f33a228cc",
    "contracts/semantic-contract/v1.0/semantic-contract-current-resolution-request.schema.json": "e13a7f7eab092cf701116e7e1b92b164ea473499",
    "contracts/semantic-contract/v1.0/semantic-contract-current-resolution-result.schema.json": "b7835693772b8e266f7fcf01fe8643d9fee320cf",
    "contracts/semantic-contract/v1.0/semantic-contract-current-selection.schema.json": "c896a1c0886ce7ee2538c1e48eb210812e6c0a68",
    "contracts/semantic-contract/v1.0/semantic-contract-policy.schema.json": "d7719af411340a2d0a9ffd11a9dcc4067ffd601c",
    "contracts/semantic-contract/v1.0/semantic-contract-profile.schema.json": "9d772051979200ca0dd3ba05fd23a9d5ccd00233",
    "contracts/semantic-contract/v1.0/semantic-contract-qualification.schema.json": "07c19f12216c27e37d6aabb9b58266c7c01cf788",
    "contracts/semantic-contract/v1.0/semantic-contract-set.schema.json": "a44426b6f28e7c2378fc82713e74d8b37c2110dd",
    "contracts/semantic-contract/v1.0/semantic-contract-version.schema.json": "c2b9bf4e11e41925c2c590773f201e417449823f",
    "contracts/semantic-contract/v1.0/sets/scs-v1-sha256-2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020.json": "a038827f86a122d71bb8ae148f69bf7e1acc8598",
    "contracts/semantic-contract/v1.0/sets/scs-v1-sha256-d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6.json": "361a336464c8ce0dc1bf936145066dd4b8d6be8f",
    "contracts/semantic-core/v1.0/contract.json": "feefb29db71311511cee99e56b5a0ea437692bed",
    "contracts/semantic-core/v1.0/vectors/architecture-reference-validation.json": "b2baf11a77b89bf9d62ed4f568421e1b6b03c129",
    "contracts/semantic-core/v1.0/vectors/architecture-validation.json": "6f3acb04fb52f1c95d547d761cb1c04569c78fea",
    "contracts/semantic-core/v1.0/vectors/attribution-shim-generation.json": "0d7a7800c15d5f058a0abae81e6131ac9e84f08a",
    "contracts/semantic-core/v1.0/vectors/contract-validation.json": "04f93361a8bbe3dc9cbb9e9b090c206ef3011405",
    "contracts/semantic-core/v1.0/vectors/embodiment-linkage.json": "4e1b6d0742450089f307e5173a2594da3c285162",
    "contracts/semantic-core/v1.0/vectors/generated-artifact-classification.json": "1939cf8e6b3c6a37ae8ea0347cf87da0295b1517",
    "contracts/semantic-core/v1.0/vectors/project-metadata-validation.json": "f62234cbeff193b5711f77e127a2e1781442e980",
    "contracts/semantic-core/v1.0/vectors/repository-validation.json": "a3fbe2e55e251581c7f92d2bc4d7df93db91239b",
    "contracts/semantic-core/v1.0/vectors/semantic-contract-set-governance.json": "462a8bfbbb031b48f8108e21b3c9dd23a5c09b68",
    "contracts/semantic-core/v1.0/vectors/semantic-contract.json": "85f86ee56d8de2630178ece389a49b8bfc5b35c5",
    "contracts/semantic-core/v1.1/contract.json": "3e9e38384b7f36bc04c50b58242c974292a29605",
    "contracts/semantic-core/v1.1/vectors/architecture-materialization.json": "0e054c589826b9af355df4f9b58acc0e9166efdc",
    "contracts/semantic-core/v1.2/contract.json": "8f622021fae39324506a99f332c3ca2e269e876e",
    "contracts/semantic-core/v1.2/vectors/authoring-construction-transport.json": "440f629a758eab3128a32b528aaf10323d2556ac",
    "contracts/semantic-core/v1.3/contract.json": "288b12a63515dafafd0ddb4329cd95727bd39577",
    "contracts/semantic-core/v1.4/contract.json": "5c1215c85f64ae82b2db1bba9c0f43789d13330b",
    "contracts/semantic-core/v1.5/contract.json": "1eec4dfdd1e08ff285accd0d1ed3c338b61aa3b4",
    "schema/architecture-discovery/v1.1/architecture-index.schema.json": "6ea0b1ba4e4ee3ffadd8b066dc599309c2bdd85f",
    "schema/architecture-discovery/v1.1/entity-registry.schema.json": "f44719ac4c8aac312be3518e7cf058d890a0c55c",
    "schema/authoring/v1.2/adr-common.schema.json": "3a9a2e35072b8a2eb7f3125123fab1a0d83f8841",
    "schema/authoring/v1.2/adr-logical.schema.json": "9d92cbcc92f96293f472ee104eae655b10622f4b",
    "schema/authoring/v1.2/adr-physical-base.schema.json": "f849ef4bbaf3cfb88d0f337802beba3b9a57fbee",
    "schema/authoring/v1.2/adr-physical-component.schema.json": "072d345540418bea7daf30fa703a98d696ae758a",
    "schema/authoring/v1.2/adr-physical-system.schema.json": "042ae8ad55f0c3f764ae1813c9e31f87e47e01e2",
    "schema/authoring/v1.2/adr-physical.schema.json": "38acdaa0d9879b37585fbc13a52e3e5e6503ba29",
    "schema/authoring/v1.2/invariant.schema.json": "7ebf1606d24b1a4609437df85c4d0efd025b07cc",
    "schema/authoring/v1.2/types.schema.json": "347f38957c4d5fbb3b53551c2b21e537d2ef861e",
    "schema/authoring/v1.3/adr-common.schema.json": "2889e4202355d7bab3c0cf1a17c7230144b7f0be",
    "schema/authoring/v1.3/adr-logical.schema.json": "88b36baac73095f5f353700c3fa91c60269905d1",
    "schema/authoring/v1.3/adr-physical-base.schema.json": "1ebc301ddd55200bd9e9c872f9dce3648ded1f71",
    "schema/authoring/v1.3/adr-physical-component.schema.json": "ad6bbd650a5f3252564c0f12fc7962c6477f41e0",
    "schema/authoring/v1.3/adr-physical-system.schema.json": "6727a390ceef59a4c88a1f66510805a6a5d1a6b1",
    "schema/authoring/v1.3/adr-physical.schema.json": "a23944930e0e501b60902224f0c2980625e9ca54",
    "schema/authoring/v1.3/types.schema.json": "fbd8bf49d5c6be7aae91983cfd65dd438fc3f20a",
    "schema/authoring/v1.4/adr-common.schema.json": "8e527cf919d9436b6f1124672b4a7c73dafbc001",
    "schema/authoring/v1.4/adr-logical.schema.json": "b380af8c5bf9f547e43fe5462e174d0a22692028",
    "schema/authoring/v1.4/adr-physical-base.schema.json": "2bfd87d9b11dc7528fed2373cb829a114442c3f2",
    "schema/authoring/v1.4/adr-physical-component.schema.json": "3760588615d317366e2d6f6d935dbb4d3f4b208d",
    "schema/authoring/v1.4/adr-physical-system.schema.json": "136b683bebc6bad9948a63486d0656a1ec707701",
    "schema/authoring/v1.4/adr-physical.schema.json": "cf3808fa9a930196c72ec45f9288f500fab60394",
    "schema/authoring/v1.4/types.schema.json": "f9618ab2dd73168a2c8373eb8e8a0d5fb9efe4d6",
    "schema/authoring/v1.5/adr-common.schema.json": "8742fc72bec6deb19fa23bb9aba24abbc55bba6a",
    "schema/authoring/v1.5/adr-logical.schema.json": "2e8970ea00e9d17b0f72dd3f39f4552b42374258",
    "schema/authoring/v1.5/adr-physical-base.schema.json": "a6d1d632832df1e834fe31209cc9bd365a3db387",
    "schema/authoring/v1.5/adr-physical-component.schema.json": "4d3840293e9fb4422da29f13dddee59f6053e54a",
    "schema/authoring/v1.5/adr-physical-system.schema.json": "515337837f872e421ebe2cb012b6ac152e452457",
    "schema/authoring/v1.5/types.schema.json": "20a7e04e978d6aacf6ddbcce26cf5788726d6d91",
    "schema/authoring/v1.6/adr-common.schema.json": "c8d403e54b155144f337388f305697ebdde6b603",
    "schema/authoring/v1.6/adr-logical.schema.json": "a68a4bad72d091d714d1c0459df1b7a1c4f82e4c",
    "schema/authoring/v1.6/adr-physical-base.schema.json": "6f747066e5dd64a015072d3908fa0baf86865213",
    "schema/authoring/v1.6/adr-physical-component.schema.json": "e293c45dcbf7a7a38df0fd6d8b7f4a2dc3f2fa3e",
    "schema/authoring/v1.6/adr-physical-system.schema.json": "985a4b2f0eec608a64b245cbd22704ce22c078a6",
    "schema/authoring/v1.6/types.schema.json": "4825ec219d528894dcc1d9446552a1db880c084b",
    "schema/authoring/v1.7/adr-common.schema.json": "ba8e11a19b7fb329dcd8c3a2332f20ef75ce87b7",
    "schema/authoring/v1.7/adr-logical.schema.json": "5adc9ff1064faa6c30eb47fcb7544f74d88d019d",
    "schema/authoring/v1.7/adr-physical-base.schema.json": "9f67d1e4feeb0dfb18f4c21a2bb2035b8c6343e0",
    "schema/authoring/v1.7/adr-physical-component.schema.json": "ff224da9fb83a92133731acf0a05130bf207c9b4",
    "schema/authoring/v1.7/adr-physical-system.schema.json": "efb87b2c4ed5ce4a8c8215df993c1125a0da5f25",
    "schema/authoring/v1.7/types.schema.json": "65b510d52d2036d3807ec7725600f163ca6543fb",
    "schema/evidence-attribution/v1.1/implementation-attribution-evidence.schema.json": "88dbff2f2d4af01b02f9f3d847d1a2234eda90a1",
    "schema/evidence-attribution/v1.1/workspace-attribution-federation.schema.json": "6aafc026290882731982ad006b76daa09a2b332f",
    "schema/evidence-attribution/v1.5/implementation-attribution-evidence.schema.json": "54d3f6f48a71ef0dda4950e31ab5f330df2f6a89",
    "schema/evidence-attribution/v1.5/semantic-attribution-vocabulary.json": "d53d50b0955d2545ba3c5682ddaa49848970c4dc",
    "schema/evidence-attribution/v1.6/implementation-attribution-evidence.schema.json": "9055f1a8a3e0578b65ce9ff7aa1f59036045397e",
    "schema/evidence-attribution/v1.6/semantic-attribution-vocabulary.json": "b86f050130f310c5decd276d24de04291e8723f3",
    "schema/governance/v1.1/decision-ledger.schema.json": "63751f3174f74bc816a1dc44809d5be731a002e1",
    "schema/governance/v1.1/objection-override.schema.json": "3e5c685d683b888e68f82abc06212e4c25a5c216",
    "schema/governance/v1.1/remediation-ledger.schema.json": "55aacefbc87997ab4924d858d078a55a36eb33b8",
    "schema/governance/v1.1/requirements-snapshot.schema.json": "5a687fa29f23f8d52e967122955080f1ee9b67e4",
    "schema/governance/v1.1/steelman-review.schema.json": "ff4fed5068e7e846b0c5165278f562b27c06fe1a",
    "schema/kernel/architecture-index.schema.json": "edb38a429bf99b996f8f87f30868cc005454f047",
    "schema/kernel/entity-registry.schema.json": "4b488f7bcb77ff06238abd597ae4d9a504bc7035",
    "schema/kernel/relationship-registry.schema.json": "7b7b9b8c469314106394cab62010125f50b3b24d",
    "schema/kernel/unresolved-registry.schema.json": "82bb681026907de3ef164140b338f1a6ea93a04c",
    "schema/migrations/canonical-identity-v13-map.schema.json": "f72edec84a3ac5ec1e0bdad9fa643ef891f97ae4",
    "schema/normalized-model/v1.1/normalized-entity-registry.schema.json": "2935a0a24b4ffdcdf8112bc14a3d29b601aa5b4d",
    "schema/normalized-model/v1.1/relationship-registry.schema.json": "d40fb0705d48ea6c2df5836e978d533275ece4db",
    "schema/normalized-model/v1.1/unresolved-registry.schema.json": "b524c78ce6d230ffabda7d1e04b8434ee6807b18",
    "schema/normalized-model/v2.0/normalized-architecture-model.schema.json": "ad7095750527fa79ba8b1d90945bb00d664adbc9",
    "schema/normalized-model/v2.0/normalized-entity-registry.schema.json": "79b9c919682738839f6c3e3065c5c4366c8f57a0",
    "schema/normalized-model/v2.0/normalized-entity.schema.json": "9fe27453901d712dd13e0987606c0eae758827b6",
    "schema/normalized-model/v2.0/relationship-record.schema.json": "0da18094c61fc7ba8bea7ea6a54d27f6985061a1",
    "schema/normalized-model/v2.0/relationship-registry.schema.json": "d9e6f2c3d939c21bc87fb3c5b3ca3f391b19a42e",
    "schema/normalized-model/v2.1/normalized-architecture-model.schema.json": "f69acadf03514a64a4e5d57fe5897cb5af0d161d",
    "schema/normalized-model/v2.1/normalized-entity-registry.schema.json": "b0306d176983e44bfa0aebe286ba14388016108c",
    "schema/normalized-model/v2.1/normalized-entity.schema.json": "bc0cfd531ae483fdd2fe2ec3712a2b90ed109dab",
    "schema/normalized-model/v2.1/relationship-record.schema.json": "d8e5ef606d15aca9c40dab65d1e2100a46686455",
    "schema/normalized-model/v2.1/relationship-registry.schema.json": "637c0df5b17d7e8ca16373f0e028c616b794f5b8",
    "schema/normalized-model/v2.1/unresolved-registry.schema.json": "9f6f58f0e0b995c7e4cc38654e7f328dc917cb82",
    "schema/normalized-model/v2.2/normalized-architecture-model.schema.json": "380dfe8ae10057927970ac6e4b305958f2a47911",
    "schema/normalized-model/v2.2/normalized-entity-registry.schema.json": "e70ac89637f680acbaa8d8d016494c137045f1ef",
    "schema/normalized-model/v2.2/normalized-entity.schema.json": "6feb741e766ce4773b35eaa05ab15fb17d79a079",
    "schema/normalized-model/v2.2/relationship-record.schema.json": "4c968023793476e2810d79eeff69cb9392fb3b06",
    "schema/normalized-model/v2.2/relationship-registry.schema.json": "b8069f116aa885251976a042677b12970c686b06",
    "schema/normalized-model/v2.2/unresolved-registry.schema.json": "7685ea988050b741355ff7cb878eef1ff2367c17",
    "schema/normalized-model/v2.3/normalized-architecture-model.schema.json": "c5caf6b3f008b9d32dacaeed9d251e2978773004",
    "schema/normalized-model/v2.3/normalized-entity-registry.schema.json": "c3ba0f7648127dc874bf6887bf59dc33e430bcab",
    "schema/normalized-model/v2.3/normalized-entity.schema.json": "cc5bd2bac84978bd3a82fa99b480767df21d8926",
    "schema/normalized-model/v2.3/relationship-record.schema.json": "e3e3ebe44c510f83e8b819fd2b07efbf8aa8a24d",
    "schema/normalized-model/v2.3/relationship-registry.schema.json": "f48a86f505c95cb4b426f2183d68f0273e4da0e2",
    "schema/normalized-model/v2.3/unresolved-registry.schema.json": "a53140c599338ae13f285c29a6ac18315e204958",
    "schema/normalized-model/v2.4/normalized-architecture-model.schema.json": "51ab6b0fc9538696946a7bd617600898fda16e4b",
    "schema/normalized-model/v2.4/normalized-entity-registry.schema.json": "36cfa43d043f52a6e5f716958f33925580f92cf3",
    "schema/normalized-model/v2.4/normalized-entity.schema.json": "392c89dc7cfd91dfa2e93ba08448cac9b9d63c9c",
    "schema/normalized-model/v2.4/relationship-record.schema.json": "1fe37c1195387bcd7e8eeb791f6dca0df3295588",
    "schema/normalized-model/v2.4/relationship-registry.schema.json": "8d0c87b1d460e1c3d15f72693eca74278331718f",
    "schema/normalized-model/v2.4/unresolved-registry.schema.json": "3a799c04c6c3244034422d380711e862f1bc0146",
    "schema/normalized-model/v2.5/normalized-architecture-model.schema.json": "3636ada2596ceef1346eec2139e71e41d2fb8995",
    "schema/normalized-model/v2.5/normalized-entity-registry.schema.json": "5423e7691ef7f164520700a0f000d150b8e48434",
    "schema/normalized-model/v2.5/normalized-entity.schema.json": "ba5695c3825ff68c8e9e25105c333bc9d61ba75e",
    "schema/normalized-model/v2.5/relationship-record.schema.json": "17a20848fc6e2c6978b9ef3f766174a8d1a390d9",
    "schema/normalized-model/v2.5/relationship-registry.schema.json": "cd50b77e12b260630482cb372250a1aeae6d8a3b",
    "schema/normalized-model/v2.5/unresolved-registry.schema.json": "98df9d01073e0ec0d9e51db803f3198bb340b82f",
    "schema/v1.0/adr-common.schema.json": "289138359b22a1add7d7ec55ace6fa22788137da",
    "schema/v1.0/adr-logical.schema.json": "716785df9d67a48032690d697173ce7e560a234e",
    "schema/v1.0/adr-physical-base.schema.json": "14abfb2f341ae5e9095f951179bb621fa73b6f74",
    "schema/v1.0/adr-physical-component.schema.json": "9fa0e1c1dca5268237489fe611bc1b8af18ff5d1",
    "schema/v1.0/adr-physical-system.schema.json": "33b6d9fb292a276f2218db428b695d0b836f21be",
    "schema/v1.0/adr-physical.schema.json": "549ca328a2d439a7239aae86e56ed553786a697d",
    "schema/v1.0/invariant.schema.json": "d4444ae2bbf73f17ce23f164f7076218e548299b",
    "schema/v1.0/manifest.schema.json": "634068fbe5cf02751e953d7612748fc41be0bec3",
    "schema/v1.0/project-metadata.schema.json": "becd618f076cdc0d9daac2060a7d0f07bdceba06",
    "schema/v1.0/types.schema.json": "1786b00446456b9e9bd2218a162dac0cd7a3c247",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.1.json": "71b7248658c387a7bf23ac3cc51317d4d696b9b6",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.2.json": "e297a2fcbe07ba47cebcbc873d11b82249004dc5",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.3.json": "68621fa69255cefda6780ab2b7ee4edcd96d8aca",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation.json": "9f044344c33fc3479549d5558675451d48574a75",
    "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.0.json": "b00fd399e1870b9577f8f7ec54dfc67f66196069",
    "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.1.json": "14981aefe18f9780152f0f96348e29e00a2f8cab",
    "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.2.json": "1918ad7eb7bf27ef2de187dc0215f6f399f3dc2b",
    "src/adr_kit/semantic_contract/v1_0/catalog/semantic-contract-catalog-1.0.json": "4659545c9b93af7b7e72d93a404ad8e4930f5bb5",
    "src/adr_kit/semantic_contract/v1_0/current/semantic-contract-current-1.0.json": "4383eb0bf08795823bed583b4169eb0a2bf4e677",
    "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.1.json": "71b7248658c387a7bf23ac3cc51317d4d696b9b6",
    "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.2.json": "e297a2fcbe07ba47cebcbc873d11b82249004dc5",
    "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.3.json": "68621fa69255cefda6780ab2b7ee4edcd96d8aca",
    "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.0.json": "b00fd399e1870b9577f8f7ec54dfc67f66196069",
    "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.1.json": "14981aefe18f9780152f0f96348e29e00a2f8cab",
    "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.2.json": "1918ad7eb7bf27ef2de187dc0215f6f399f3dc2b",
    "src/adr_kit/semantic_contract/v1_0/definitions/normalized-model-2.4.json": "a0559a5bda8fd65b90b5b0d9b79949c745df464c",
    "src/adr_kit/semantic_contract/v1_0/definitions/normalized-model-2.5.json": "cfcd46fa7aefced4213274fc26969dca1b05983c",
    "src/adr_kit/semantic_contract/v1_0/definitions/normative-semantics-1.0.json": "2ae295dee7b7f6a9d353839ec8b019798a670464",
    "src/adr_kit/semantic_contract/v1_0/normalized-model-2.4.json": "a0559a5bda8fd65b90b5b0d9b79949c745df464c",
    "src/adr_kit/semantic_contract/v1_0/normalized-model-2.5.json": "cfcd46fa7aefced4213274fc26969dca1b05983c",
    "src/adr_kit/semantic_contract/v1_0/normalized-model.json": "6b49bd32ff0fd91198a531654c911da1e9f4e925",
    "src/adr_kit/semantic_contract/v1_0/normative-semantics-1.0.json": "2ae295dee7b7f6a9d353839ec8b019798a670464",
    "src/adr_kit/semantic_contract/v1_0/normative-semantics.json": "2ae295dee7b7f6a9d353839ec8b019798a670464",
    "src/adr_kit/semantic_contract/v1_0/policy/semantic-contract-policy-1.0.json": "363e8535ddc8f5fdffcc7f375ebb9b13bf40f562",
    "src/adr_kit/semantic_contract/v1_0/profiles/architecture-materialization-1.0.json": "e0ff9a7b0f2a82040c311b1e8fa1df806db309a8",
    "src/adr_kit/semantic_contract/v1_0/profiles/architecture-materialization-1.1.json": "5a5647ee5b1157da995d1e2bf70d5f30d471137b",
    "src/adr_kit/semantic_contract/v1_0/qualifications/architecture-materialization-1.0.json": "3e7921f14ff09dcc360beb8c02d36e4a7f6aa115",
    "src/adr_kit/semantic_contract/v1_0/qualifications/architecture-materialization-1.1.json": "65e130f71eb9d5f80757146e8733ebe88b641cee",
    "src/adr_kit/semantic_contract/v1_0/resource-manifest-entry.schema.json": "217cd4b79e7f780f0042b1a060b8b725c8498f47",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-conformance.json": "3d544df0eb35148725f3f1231985068f313f42c9",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-legacy-compatibility.json": "20dab4078340a553f943028ff316f2c041fb9f85",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-rules.json": "a8bf737bc500dcda62ae50ea35e70fca9959c3ab",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-source-decoding-1.7.json": "b37b8c8dd552c5b386789d16f18e9b9368bfee25",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-source-mapping-1.7-to-2.4.json": "ffabe9db796812ca0ad2d5db5ceb6aa56949e3ac",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-conformance.json": "35b6d3cbeffa942e8cec7c1348d6aa643a55f5f4",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-conformance.schema.json": "c92e33564d658ad32e10842190aa86ac9ea241b6",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-contract.json": "e297a2fcbe07ba47cebcbc873d11b82249004dc5",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-detached-context.json": "02a9714f20fe663129ed0be82beef34f0d70bd62",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-field-dispositions-1.7-to-2.4.json": "16d64c3fa69159225c812c175c29cfc79f1cc8e8",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-field-dispositions.schema.json": "7463f6f1f7240340573101a712a970882df8b010",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-legacy-compatibility.json": "b8425ce9daedf65f929683c0a4dfa2c550b649b7",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-rules.json": "e111b553d684101772dd23948270400757224ccf",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-source-decoding-1.7.json": "23df3eda244ded4cd75982fbb54ac33b541768dd",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-source-mapping-1.7-to-2.4.json": "6085e4a7e60e867b4171d05652a935730f53f6f0",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-conformance.json": "5b73625e351e1c2a3be7b6a8e845128238872b7c",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-conformance.schema.json": "373884821668639beec7567ebbfeeb98395dd6f6",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-contextual-facts.json": "52fb92511715b4761c5908b8f1b60a55a642eb46",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-contextual-facts.schema.json": "4078c232d9cc86e3075308037c64299abcc0fd06",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-detached-context.json": "256614a2b48b4ba373244aa31afb59bb879288d7",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-field-dispositions-1.7-to-2.5.json": "50826ad1f5eaeac99b8cfe6f3247d20bc55b5414",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-field-dispositions.schema.json": "335aebbcda9a961864b8ee4411aed9216838be9d",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-lifecycle-ownership.json": "f685c1aafb394054b5401091e7f8cb27f339ed8c",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-lifecycle-ownership.schema.json": "bb3315d5e3b107bdd71943ba25aea4f5401f9833",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-lifecycle-provenance.schema.json": "6eb602a1048a1bcd0dd1f3f3a708d0247d5074d7",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-rules.json": "e0f8410c671f4c329bb1c921c859092b6daac918",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.3-source-mapping-1.7-to-2.5.json": "a5112f12b4e7eceec0834200c2497d1a82403096",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-conformance.json": "5d08a88e11400b7999282c0e80213b7554098794",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-rules.json": "838b93f10b0a53d1ec143fc549df537bac2f2615",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-source-decoding-1.5.json": "70494489a90c0575be39d578c9a02eb393a77e7a",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-source-decoding-1.6.json": "514f306d1f4e232f2e78119a4678ceeb646cb89a",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-source-mapping-1.5-to-2.3.json": "90bfc54232432de2fef5d4a86f778491e1a37b5c",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-source-mapping-1.6-to-2.3.json": "d6d1d6bae242d4de7a30e82e6094fabc4654914f",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-common.schema.json": "8742fc72bec6deb19fa23bb9aba24abbc55bba6a",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-logical.schema.json": "2e8970ea00e9d17b0f72dd3f39f4552b42374258",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-physical-base.schema.json": "a6d1d632832df1e834fe31209cc9bd365a3db387",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-physical-component.schema.json": "4d3840293e9fb4422da29f13dddee59f6053e54a",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-physical-system.schema.json": "515337837f872e421ebe2cb012b6ac152e452457",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-types.schema.json": "20a7e04e978d6aacf6ddbcce26cf5788726d6d91",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-common.schema.json": "c8d403e54b155144f337388f305697ebdde6b603",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-logical.schema.json": "a68a4bad72d091d714d1c0459df1b7a1c4f82e4c",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-physical-base.schema.json": "6f747066e5dd64a015072d3908fa0baf86865213",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-physical-component.schema.json": "e293c45dcbf7a7a38df0fd6d8b7f4a2dc3f2fa3e",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-physical-system.schema.json": "985a4b2f0eec608a64b245cbd22704ce22c078a6",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-types.schema.json": "4825ec219d528894dcc1d9446552a1db880c084b",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-common.schema.json": "ba8e11a19b7fb329dcd8c3a2332f20ef75ce87b7",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-logical.schema.json": "5adc9ff1064faa6c30eb47fcb7544f74d88d019d",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-physical-base.schema.json": "9f67d1e4feeb0dfb18f4c21a2bb2035b8c6343e0",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-physical-component.schema.json": "ff224da9fb83a92133731acf0a05130bf207c9b4",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-physical-system.schema.json": "efb87b2c4ed5ce4a8c8215df993c1125a0da5f25",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-types.schema.json": "65b510d52d2036d3807ec7725600f163ca6543fb",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.0-conformance.json": "ea0cd027cf5222695463905246b06ba9e3cfcebe",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.0-contract.json": "b00fd399e1870b9577f8f7ec54dfc67f66196069",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.0-rules.json": "c4e877be8e1b17ff18461b5eacf241d7235d72d7",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-compatibility.json": "d50a9cf1187bd57a0ab43801bf9104d4bb29a87a",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-conformance.json": "7a2615ba5f9fd776c26bd7cbf17cd098011ab334",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-conformance.schema.json": "0028f3e2fa6f7b44a3147f7e4b7afac275857a17",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-contract.json": "14981aefe18f9780152f0f96348e29e00a2f8cab",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-ledger.schema.json": "4e14a67d12abd8e1440caf6ed9d49b411804a3cc",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-rules.json": "5b58d44bbf946df810eaa55fe84b09345fe4e977",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-schema.json": "9cfc45094ec484e9dad5f2dbe38c2ca3c1bbd94d",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-compatibility.json": "8548cc25585e68dc557ccfa14c7617c1b10ae64c",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-composition-bindings.json": "7c2efa4107bf8f3d4009d5957168e7bdf95a1fd4",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-composition-bindings.schema.json": "b32c8db7a49ff32c5858d2ceffb1a1fc9265531e",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-conformance.json": "a2c9d403eb6717be9efd71475d3079dae9737286",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-conformance.schema.json": "e3ab956b30b055840f3c5048eebb73532d79d0f3",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-rules.json": "26f05bc8339c2ef00c3ee441c90aa37d41aa8dc1",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-schema.json": "b731adaaa83d896db318964965bb1de10f6eb0d8",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-domain-1.1-contract.json": "141bb3eef837651a6cbe7ba48b0b57c4bac46cd5",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-domain-1.1-schema.json": "f34a32283010be36b6bed5f38b3a05df65b521e9",
    "src/adr_kit/semantic_contract/v1_0/resources/custom-entity-1.0-conformance.json": "040724768316afd3c8899582f99647cf6ed7d1cd",
    "src/adr_kit/semantic_contract/v1_0/resources/custom-entity-1.0-contract.json": "9a55aedcad61a7342ac626567302bc311b9b6adf",
    "src/adr_kit/semantic_contract/v1_0/resources/custom-entity-1.0-schema.json": "5ae8eddcd5d1ca887fe52a92855ebb4ed390201c",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-conformance.json": "56819288be8a0fb47d29930acb702a8d8d59ec93",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-normalized-architecture-model.schema.json": "c5caf6b3f008b9d32dacaeed9d251e2978773004",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-normalized-entity-registry.schema.json": "c3ba0f7648127dc874bf6887bf59dc33e430bcab",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-normalized-entity.schema.json": "cc5bd2bac84978bd3a82fa99b480767df21d8926",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-relationship-record.schema.json": "e3e3ebe44c510f83e8b819fd2b07efbf8aa8a24d",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-relationship-registry.schema.json": "f48a86f505c95cb4b426f2183d68f0273e4da0e2",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-unresolved-registry.schema.json": "a53140c599338ae13f285c29a6ac18315e204958",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-conformance.json": "47ec0af3b6c59774aacc85ed6ef4eddbe2a63b3a",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-architecture-model.schema.json": "51ab6b0fc9538696946a7bd617600898fda16e4b",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-entity-registry.schema.json": "36cfa43d043f52a6e5f716958f33925580f92cf3",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-entity.schema.json": "392c89dc7cfd91dfa2e93ba08448cac9b9d63c9c",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-relationship-record.schema.json": "1fe37c1195387bcd7e8eeb791f6dca0df3295588",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-relationship-registry.schema.json": "8d0c87b1d460e1c3d15f72693eca74278331718f",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-unresolved-registry.schema.json": "3a799c04c6c3244034422d380711e862f1bc0146",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-conformance.json": "a8dc61f59e2e78f24ed1bcaea2d46fb82260c988",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-normalized-architecture-model.schema.json": "3636ada2596ceef1346eec2139e71e41d2fb8995",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-normalized-entity-registry.schema.json": "5423e7691ef7f164520700a0f000d150b8e48434",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-normalized-entity.schema.json": "ba5695c3825ff68c8e9e25105c333bc9d61ba75e",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-relationship-record.schema.json": "17a20848fc6e2c6978b9ef3f766174a8d1a390d9",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-relationship-registry.schema.json": "cd50b77e12b260630482cb372250a1aeae6d8a3b",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-unresolved-registry.schema.json": "98df9d01073e0ec0d9e51db803f3198bb340b82f",
    "src/adr_kit/semantic_contract/v1_0/resources/normative-semantics-conformance.json": "d71f955a91cf0c3dbb9349560dd55ff4819bbdac",
    "src/adr_kit/semantic_contract/v1_0/resources/normative-semantics-definition.json": "03ccd326feebb77b3b28c486c93fdf7e2a9c7e46",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-assembly-request.schema.json": "993460bf51d68f694749b07c1b97303d163db861",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-assembly-result.schema.json": "36ece4eafd877f5ac70788e22f7829de43bc16b6",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-catalog.schema.json": "b2fd72609c2e31a5cb43b54f5d9fcc36364084ef",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-corpus-validation-request.schema.json": "5aa34bd05786d453c9d3b6ec3533841244285fd2",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-corpus-validation-result.schema.json": "0ffbaa509311db79c8849aab33a2075f33a228cc",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-current-resolution-request.schema.json": "e13a7f7eab092cf701116e7e1b92b164ea473499",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-current-resolution-result.schema.json": "b7835693772b8e266f7fcf01fe8643d9fee320cf",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-current-selection.schema.json": "c896a1c0886ce7ee2538c1e48eb210812e6c0a68",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-policy.schema.json": "d7719af411340a2d0a9ffd11a9dcc4067ffd601c",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-profile.schema.json": "9d772051979200ca0dd3ba05fd23a9d5ccd00233",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-qualification.schema.json": "07c19f12216c27e37d6aabb9b58266c7c01cf788",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-set.schema.json": "a44426b6f28e7c2378fc82713e74d8b37c2110dd",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-version.schema.json": "c2b9bf4e11e41925c2c590773f201e417449823f",
    "src/adr_kit/semantic_contract/v1_0/sets/scs-v1-sha256-2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020.json": "a038827f86a122d71bb8ae148f69bf7e1acc8598",
    "src/adr_kit/semantic_contract/v1_0/sets/scs-v1-sha256-d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6.json": "361a336464c8ce0dc1bf936145066dd4b8d6be8f",
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def bundle() -> list[dict[str, Any]]:
    return [
        {
            "canonicalResourceKey": e.canonical_resource_key,
            "content": load_semantic_resource(e.canonical_resource_key),
        }
        for e in get_semantic_contract("authoring-construction", "1.3").resource_manifest
    ]


def validator(name: str = "schema", fragment: str = "") -> Draft202012Validator:
    documents: dict[str, Resource[Any]] = {}
    for entry in bundle():
        value = entry["content"]
        if isinstance(value, dict) and "json-schema.org/" in value.get("$schema", ""):
            resource = Resource.from_contents(value)
            if "$id" in value:
                documents[value["$id"]] = resource
            documents[
                "https://adr-kit.dev/semantic-contract/resources/"
                + entry["canonicalResourceKey"]
                + ".json"
            ] = resource
    registry: Registry[Any] = Registry().with_resources(documents.items())
    path = BASE / ("schema.json" if name == "schema" else "resources/" + name + ".json")
    schema = read(path)
    if fragment:
        schema = {"$ref": schema["$id"] + "#/$defs/" + fragment}
    return Draft202012Validator(schema, registry=registry)


def request() -> dict[str, Any]:
    from tests.test_authoring_construction_v11_contract import _minimal_acc11_request

    value = _minimal_acc11_request()
    value["contract_version"] = "1.3"
    value["basis"]["acc"].update(version="1.3", semantic_contract_fingerprint=SCF)
    for prop, definition in [
        ("architecture_interpretation", "exact_ai13_closure"),
        ("normalized_model", "exact_nm25_closure"),
        ("authoring", "exact_authoring17_closure"),
    ]:
        schema = read(BASE / "schema.json")["$defs"][definition]
        qualification = {
            "family": schema["properties"]["family"]["const"],
            "version": schema["properties"]["version"]["const"],
            "resources": schema["properties"]["resources"]["items"]["enum"],
        }
        if prop == "architecture_interpretation":
            value["basis"][prop] = {
                "family": "architecture-interpretation",
                "version": "1.3",
                "semantic_contract_fingerprint": publication.AI_SCF,
                "authority_closure": qualification,
            }
        else:
            value["basis"][prop] = qualification
            if prop == "normalized_model":
                qualification["semantic_contract_fingerprint"] = publication.NM_SCF
    return value


def inherited_ledger() -> dict[str, Any]:
    row = publication.selected(ROOT, "lifecycle-ownership")["rows"][0]
    return {
        "ledger_version": "authoring-construction-semantic-ledger/1.3",
        "semantic_units": [
            {
                "semantic_type": row["child_semantic_type"],
                "identity": {"identity_kind": "canonical_uuidv7", "components": [UUID]},
                "lifecycle_stage": "accepted",
                "fields": [
                    {
                        "semantic_field_key": publication.CONTEXT_KEY,
                        "value": {
                            "declaring_adr_id": "01900000-0000-7000-8000-000000000001",
                            "declaring_adr_semantic_type": row["declaring_adr_semantic_type"],
                            "status_semantic_field_key": row["status_semantic_field_key"],
                            "ownership_rule": {"rule_id": row["rule_id"]},
                        },
                    }
                ],
            }
        ],
        "relationships": [],
        "unresolved": [],
    }


def test_exact_scf_manifest_schema_and_closure() -> None:
    c = get_semantic_contract("authoring-construction", "1.3")
    assert c.semantic_contract_fingerprint == SCF
    assert calculate_semantic_contract_fingerprint(c).semantic_contract_fingerprint == SCF
    assert verify_semantic_contract(c).success
    assert len(c.resource_manifest) == 94
    assert c.frozen_normative_conformance_resources == (publication.PREFIX + "conformance",)
    assert validate_semantic_resource_closure(c, bundle()).closure_valid
    assert validate_semantic_resource_closure(c, list(reversed(bundle()))).closure_valid
    validator().validate(c.to_wire())
    result = publication.qualify(ROOT)
    assert result == {
        "composition_bindings": 1,
        "ownership_selectors": 17,
        "enum_domain_proofs": 20,
        "conformance_cases": 159,
        "runtime_execution": False,
    }


@pytest.mark.parametrize(
    "fault", ["missing", "extra", "duplicate", "tampered", "scf", "dependency"]
)
def test_immutable_closure_faults(fault: str) -> None:
    c = get_semantic_contract("authoring-construction", "1.3").to_wire()
    resources = bundle()
    if fault == "missing":
        resources.pop()
    elif fault == "extra":
        resources.append({"canonicalResourceKey": publication.PREFIX + "unknown", "content": {}})
    elif fault == "duplicate":
        resources.append(resources[-1])
    elif fault == "tampered":
        next(e for e in resources if e["canonicalResourceKey"] == publication.PREFIX + "rules")[
            "content"
        ]["lifecycle"] = {}
    elif fault == "scf":
        c["semanticContractFingerprint"] = "scf:v1:sha256:" + "0" * 64
    else:
        next(e for e in c["resourceManifest"] if e["dependencies"])["dependencies"].pop()
        c["semanticContractFingerprint"] = calculate_semantic_contract_fingerprint(
            c
        ).semantic_contract_fingerprint
    assert not validate_semantic_resource_closure(c, resources).success


def test_exact_request_qualifies_complete_selected_closures_in_any_order() -> None:
    value = request()
    v = validator(fragment="authoring_request")
    v.validate(value)
    for member in [
        value["basis"]["architecture_interpretation"]["authority_closure"],
        value["basis"]["normalized_model"],
        value["basis"]["authoring"],
    ]:
        member["resources"].reverse()
    v.validate(value)
    # Its shape is not proof of execution or the enclosing ACC SCF.
    assert (
        read(BASE / "resources/rules.json")["composition"]["request_acc_fingerprint"]
        == "must_equal_verified_enclosing_definition; never_embed_enclosing_SCF_in_resource"
    )


@pytest.mark.parametrize(
    "fault",
    [
        "acc_version",
        "AI_version",
        "AI_SCF",
        "NM_version",
        "NM_SCF",
        "AI_missing",
        "AI_digest",
        "NM_missing",
        "duplicate",
        "authoring_digest",
    ],
)
def test_request_selectors_fail_closed(fault: str) -> None:
    value = request()
    basis = value["basis"]
    if fault == "acc_version":
        basis["acc"]["version"] = "1.2"
    elif fault == "AI_version":
        basis["architecture_interpretation"]["version"] = "1.2"
    elif fault == "AI_SCF":
        basis["architecture_interpretation"]["semantic_contract_fingerprint"] = (
            "scf:v1:sha256:" + "0" * 64
        )
    elif fault == "NM_version":
        basis["normalized_model"]["version"] = "2.4"
    elif fault == "NM_SCF":
        basis["normalized_model"]["semantic_contract_fingerprint"] = "scf:v1:sha256:" + "0" * 64
    elif fault == "AI_missing":
        basis["architecture_interpretation"]["authority_closure"]["resources"].pop()
    elif fault == "AI_digest":
        basis["architecture_interpretation"]["authority_closure"]["resources"][0][
            "content_digest"
        ] = ("sha256:" + "0" * 64)
    elif fault == "NM_missing":
        basis["normalized_model"]["resources"].pop()
    elif fault == "duplicate":
        basis["normalized_model"]["resources"][-1] = basis["normalized_model"]["resources"][0]
    else:
        basis["authoring"]["resources"][0]["content_digest"] = "sha256:" + "0" * 64
    assert not validator(fragment="authoring_request").is_valid(value)


def test_single_composition_binding_and_exact_AI_ownership_qualification() -> None:
    table = read(BASE / "resources/composition-bindings.json")
    validator("composition-bindings.schema").validate(table)
    row = table["rows"][0]
    assert len(table["rows"]) == 1
    assert (
        row["parent_semantic_type"],
        row["child_semantic_type"],
        row["relation"],
        row["parent_pointer"],
    ) == ("adr/logical", "entity/decision", "contains", "/decisions")
    old = publication.predecessor(ROOT, "composition-bindings")["rows"][0]
    for key in old:
        if key != "ai_authority":
            assert row[key] == old[key]
    owner = row["ai_ownership_authority"]
    assert owner["semantic_contract_fingerprint"] == publication.AI_SCF
    assert owner["content_digest"] == publication.digest(
        publication.selected(ROOT, "lifecycle-ownership")
    )
    selected = [
        r
        for r in publication.selected(ROOT, "lifecycle-ownership")["rows"]
        if r["rule_id"] == owner["rule_id"]
    ]
    assert len(selected) == 1 and selected[0]["source_instance_pattern"] == "/decisions/*"
    rules = read(BASE / "resources/rules.json")
    for authority, name in [
        ("binding_authority", "composition-bindings"),
        ("schema_authority", "composition-bindings.schema"),
    ]:
        assert rules["composition"][authority]["content_digest"] == publication.digest(
            read(BASE / ("resources/" + name + ".json"))
        )


@pytest.mark.parametrize(
    "fault",
    ["duplicate", "relation", "property", "endpoint", "owner_digest", "owner_rule", "ai_digest"],
)
def test_binding_table_negative_shapes(fault: str) -> None:
    table = read(BASE / "resources/composition-bindings.json")
    row = table["rows"][0]
    if fault == "duplicate":
        table["rows"].append(copy.deepcopy(row))
    elif fault == "relation":
        row["relation"] = "composed_of"
    elif fault == "property":
        row["parent_pointer"] = "/gaps"
    elif fault == "endpoint":
        row["endpoint_resolution"] = "alias"
    elif fault == "owner_digest":
        row["ai_ownership_authority"]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "owner_rule":
        row["ai_ownership_authority"]["rule_id"] = "wrong"
    else:
        row["ai_authority"]["content_digest"] = "sha256:" + "0" * 64
    # The schema enforces table shape and closed qualified ownership. Digest and
    # row-policy consistency also require the independent publication qualifier.
    if fault in {"duplicate", "owner_digest", "owner_rule"}:
        assert not validator("composition-bindings.schema").is_valid(table)
    else:
        assert table != publication.binding(ROOT)


def test_inherited_ledger_value_and_context_are_separate_and_lossless() -> None:
    v = validator("ledger.schema")
    value = inherited_ledger()
    for status in ["proposed", "accepted", "deprecated", "superseded"]:
        value["semantic_units"][0]["lifecycle_stage"] = status
        v.validate(value)
    unit = value["semantic_units"][0]
    assert set(unit["fields"][0]["value"]) == {
        "declaring_adr_id",
        "declaring_adr_semantic_type",
        "status_semantic_field_key",
        "ownership_rule",
    }
    assert "lifecycle_stage" not in unit["fields"][0]["value"]
    facts = read(BASE / "resources/rules.json")["ledger"]["contextual_semantics"]
    assert (
        facts["value_projection"]
        == publication.selected(ROOT, "contextual-facts")["facts"][0]["semantic_equality_fields"]
    )
    assert (
        facts["inherited_first_class_value"]
        == "semantic_unit.lifecycle_stage_or_existing_qualified_authored_status_once_only"
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing_value",
        "missing_context",
        "duplicate_context",
        "carrier_lifecycle",
        "carrier_digest",
        "missing_owner",
        "wrong_rule",
        "normative",
        "custom",
        "owner_local",
        "root_duplicate",
        "active",
        "wrong_version",
        "wrong_child_identity",
    ],
)
def test_ledger_negative_shapes_do_not_authorize_partial_or_duplicated_lifecycle(
    fault: str,
) -> None:
    value = inherited_ledger()
    unit = value["semantic_units"][0]
    context = unit["fields"][0]["value"]
    if fault == "missing_value":
        del unit["lifecycle_stage"]
    elif fault == "missing_context":
        unit["fields"] = []
    elif fault == "duplicate_context":
        unit["fields"].append(copy.deepcopy(unit["fields"][0]))
    elif fault == "carrier_lifecycle":
        context["lifecycle_stage"] = "accepted"
    elif fault == "carrier_digest":
        context["resource_digest"] = "sha256:" + "0" * 64
    elif fault == "missing_owner":
        del context["declaring_adr_id"]
    elif fault == "wrong_rule":
        context["ownership_rule"]["rule_id"] = "unknown"
    elif fault == "normative":
        unit["semantic_type"] = "entity/normative_proposition"
    elif fault == "custom":
        unit["semantic_type"] = "entity/extension"
    elif fault == "owner_local":
        unit["semantic_type"] = "value/topology_component"
    elif fault == "root_duplicate":
        unit["semantic_type"] = "adr/logical"
    elif fault == "active":
        unit["lifecycle_stage"] = "active"
    elif fault == "wrong_version":
        value["ledger_version"] = "authoring-construction-semantic-ledger/1.1"
    else:
        unit["identity"]["components"] = ["request-key"]
    assert not validator("ledger.schema").is_valid(value)


def test_contextual_mismatch_oracle_is_not_a_runtime_comparator() -> None:
    value = inherited_ledger()
    for field in [
        "declaring_adr_id",
        "declaring_adr_semantic_type",
        "status_semantic_field_key",
        "ownership_rule",
    ]:
        changed = copy.deepcopy(value)
        changed["semantic_units"][0]["fields"][0]["value"][field] = "changed"
        assert changed != value
    rules = read(BASE / "resources/rules.json")
    assert rules["equivalence"]["fingerprint_or_count_substitution_for_ledger_equality"] is False
    assert rules["equivalence"]["provenance_substitution_for_missing_semantics"] is False
    assert rules["lifecycle"]["missing_qualified_lifecycle_provenance"] == "Unavailable"
    assert rules["outcomes"]["precedence"] == [
        "Rejected",
        "Unavailable",
        "Unresolved",
        "Constructed",
    ]
    # This test checks the frozen comparison oracle; it executes no ACC equality.
    assert rules["implementation_posture"]["whole_result_comparator"] == "not_implemented"


def test_every_selected_owner_and_literal_domain_fits_the_ledger_without_value_replay() -> None:
    v = validator("ledger.schema")
    for row in publication.selected(ROOT, "lifecycle-ownership")["rows"]:
        value = inherited_ledger()
        unit = value["semantic_units"][0]
        unit["semantic_type"] = row["child_semantic_type"]
        context = unit["fields"][0]["value"]
        context.update(
            declaring_adr_semantic_type=row["declaring_adr_semantic_type"],
            status_semantic_field_key=row["status_semantic_field_key"],
            ownership_rule={"rule_id": row["rule_id"]},
        )
        for status in ["proposed", "accepted", "deprecated", "superseded"]:
            unit["lifecycle_stage"] = status
            v.validate(value)
    proposition = inherited_ledger()
    unit = proposition["semantic_units"][0]
    unit["semantic_type"] = "entity/normative_proposition"
    unit.pop("lifecycle_stage")
    unit["fields"] = []
    v.validate(proposition)


def test_complete_NM25_result_schema_rejects_an_ACC_local_stub() -> None:
    value = {
        "normalized_contract": request()["basis"]["normalized_model"],
        "semantic_digest": "sha256:" + "0" * 64,
        "model": {},
    }
    assert not validator(fragment="normalized_result").is_valid(value)
    schema = read(BASE / "schema.json")
    assert schema["$defs"]["normalized_result"]["properties"]["model"] == {
        "$ref": "../../normalized-model/2.5/schema/normalized-architecture-model.schema.json"
    }
    for name in ["expected_ledger", "observed_ledger"]:
        assert schema["$defs"]["construction_qualification"]["properties"][name] == {
            "$ref": "ledger.schema.json"
        }


def test_shared_system_descriptor_reuses_one_owned_lifecycle_without_another_unit() -> None:
    v = validator("ledger.schema")
    value = inherited_ledger()
    unit = value["semantic_units"][0]
    unit["semantic_type"] = "adr/physical-system"
    unit.pop("lifecycle_stage")
    context = unit["fields"][0]["value"]
    context.update(
        declaring_adr_id=UUID,
        declaring_adr_semantic_type="adr/physical-system",
        status_semantic_field_key="adr/physical-system#/status",
        ownership_rule={"rule_id": "declaring-lifecycle.adr-physical-system.system"},
    )
    unit["fields"].append(
        {"semantic_field_key": "adr/physical-system#/status", "value": "accepted"}
    )
    v.validate(value)
    assert len(value["semantic_units"]) == 1
    duplicate = copy.deepcopy(value)
    duplicate["semantic_units"][0]["lifecycle_stage"] = "accepted"
    assert not v.is_valid(duplicate)
    duplicate = copy.deepcopy(value)
    duplicate["semantic_units"][0]["fields"].append(copy.deepcopy(unit["fields"][0]))
    assert not v.is_valid(duplicate)
    # Shape alone does not prove identity coincidence or select the governed unit
    # type. The published rule requires independent sealed-source qualification.
    rules = read(BASE / "resources/rules.json")["ledger"]["contextual_semantics"][
        "shared_descriptor"
    ]
    assert rules["rule"] == "reuse_existing_semantic_unit_if_same_canonical_identity"
    assert rules["schema_admission"] == "does_not_select_unit_type_or_prove_identity_coincidence"


@pytest.fixture
def candidate(tmp_path: Path) -> Path:
    for name in ("contracts", "schema"):
        shutil.copytree(ROOT / name, tmp_path / name)
    return tmp_path


@pytest.mark.parametrize(
    "fault",
    [
        "binding",
        "endpoint",
        "relation",
        "owner_rule",
        "ADC_policy",
        "AI_disposition",
        "AI_flat_bytes",
        "NM_definition",
        "missing_CEC",
        "context_rule",
        "ledger",
        "partial_result",
        "table_schema",
    ],
)
def test_publication_qualifier_rejects_inconsistent_authority(candidate: Path, fault: str) -> None:
    base = candidate / "contracts/authoring-construction/v1.3"
    name = "resources/rules.json"
    if fault in {"binding", "endpoint", "relation"}:
        name = "resources/composition-bindings.json"
    elif fault == "owner_rule":
        name = "resources/composition-bindings.json"
    elif fault == "ledger":
        name = "resources/ledger.schema.json"
    elif fault == "partial_result":
        name = "schema.json"
    elif fault == "table_schema":
        name = "resources/composition-bindings.schema.json"
    path = base / name
    if fault == "ADC_policy":
        path = candidate / "contracts/authoring-domain/v1.1/contract.json"
    elif fault == "AI_disposition":
        path = (
            candidate
            / "contracts/architecture-interpretation/v1.3/resources/field-dispositions-1.7-to-2.5.json"
        )
    elif fault == "AI_flat_bytes":
        path = (
            candidate
            / "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-rules.json"
        )
    elif fault == "NM_definition":
        path = candidate / "contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json"
    elif fault == "missing_CEC":
        (
            candidate / "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-contract.json"
        ).unlink()
        with pytest.raises((ValueError, FileNotFoundError)):
            publication.qualify(candidate)
        return
    value = read(path)
    if fault == "binding":
        value["rows"][0]["parent_pointer"] = "/gaps"
    elif fault == "endpoint":
        value["rows"][0]["endpoint_resolution"] = "alias"
    elif fault == "relation":
        value["rows"][0]["relation"] = "composed_of"
    elif fault == "owner_rule":
        value["rows"][0]["ai_ownership_authority"]["rule_id"] = "invented"
    elif fault == "ADC_policy":
        value["types"][0]["identity_policy"] = {}
    elif fault == "AI_disposition":
        value["semantic_types"][0]["field_dispositions"][0]["disposition"] = "unknown"
    elif fault == "AI_flat_bytes":
        value["identity"] = {}
    elif fault == "NM_definition":
        value["resourceManifest"].pop()
    elif fault == "context_rule":
        value["ledger"]["contextual_semantics"]["context_value_contains_lifecycle"] = True
    elif fault == "ledger":
        value["$defs"]["contextual_lifecycle_fact"]["additionalProperties"] = True
    elif fault == "partial_result":
        value["$defs"]["normalized_result"]["properties"]["model"] = {"type": "object"}
    else:
        value["properties"]["rows"]["maxItems"] = 2
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError):
        publication.qualify(candidate)


def test_authority_qualification_requires_no_ADR_or_ambient_repository(candidate: Path) -> None:
    assert not (candidate / "adrs").exists()
    assert publication.qualify(candidate)["conformance_cases"] == 159


def test_all_frozen_cases_individually_requalified_and_authority_only() -> None:
    resource = read(BASE / "resources/conformance.json")
    validator("conformance.schema").validate(resource)
    cases = resource["cases"]
    assert len(cases) == 159
    for i, old in enumerate(publication.predecessor(ROOT, "conformance")["cases"]):
        case = cases[i]
        assert case["requalified_from"] == old["case_id"]
        assert case["claim"] == publication.retarget(old["claim"])
        assert case["review"]
        assert case["assertions"][: len(old["assertions"])] == publication.retarget(
            old["assertions"]
        )
    assert all(c["runtime_coverage"] == "authority_only_not_implemented" for c in cases)
    assert Counter(c["fixture"]["input"].get("category") for c in cases[41:]) == {
        "root_lifecycle": 12,
        "ownership_selector": 68,
        "successor_boundary": 38,
    }
    assert {
        c["fixture"]["input"]["row"]["rule_id"]
        for c in cases[41:]
        if c["fixture"]["input"].get("category") == "ownership_selector"
    } == {r["rule_id"] for r in publication.selected(ROOT, "lifecycle-ownership")["rows"]}
    assert not any(
        a["path"] == "outcome" and a["expected"] == "Constructed"
        for c in cases
        for a in c["assertions"]
    )


def test_exact_discovery_missing_versions_aliases_and_publication_only() -> None:
    assert (
        get_semantic_contract("authoring-construction", "1.3").semantic_contract_fingerprint == SCF
    )
    assert (
        load_semantic_resource(publication.AI + "contract")
        == get_semantic_contract("architecture-interpretation", "1.3").to_wire()
    )
    for key in [
        "authoring-construction/1.4/rules",
        publication.PREFIX + "contract",
        publication.PREFIX + "composition/bindings",
        publication.PREFIX + "conformance-not-published",
    ]:
        with pytest.raises(LookupError):
            load_semantic_resource(key)
    with pytest.raises(LookupError):
        get_semantic_contract("authoring-construction", "1.4")
    assert all(c.semantic_contract_version != "1.3" for c in list_semantic_contracts())
    assert (
        read(BASE / "resources/rules.json")["publication_posture"][
            "execution_capability_advertised"
        ]
        is False
    )
    assert "1.3" not in str(semantic_core_capabilities().get("authoring_construction", {}))


def test_package_byte_parity_regeneration_and_historical_git_blobs() -> None:
    targets = [
        BASE / "contract.json",
        ASSETS / "definitions/authoring-construction-1.3.json",
        PACKAGE / "definitions/authoring-construction-1.3.json",
        PACKAGE / "authoring-construction-1.3.json",
    ]
    assert len({p.read_bytes() for p in targets}) == 1
    for name in publication.NAMES:
        source = BASE / ("schema.json" if name == "schema" else "resources/" + name + ".json")
        for directory in (ASSETS / "resources", PACKAGE / "resources"):
            p = directory / ("authoring-construction-1.3-" + name + ".json")
            assert p.read_bytes() == source.read_bytes()
            assert SCF not in p.read_text(encoding="utf-8")
            targets.append(p)
    for directory in (ASSETS / "resources", PACKAGE / "resources"):
        p = directory / "architecture-interpretation-1.3-contract.json"
        assert (
            p.read_bytes()
            == (ASSETS / "definitions/architecture-interpretation-1.3.json").read_bytes()
        )
        targets.append(p)
    before = {p: p.read_bytes() for p in targets}
    for _ in range(2):
        subprocess.run(
            [
                sys.executable,
                "scripts/generate_semantic_contract_assets.py",
                "--publish-acc13-only",
            ],
            cwd=ROOT,
            check=True,
        )
        assert before == {p: p.read_bytes() for p in targets}
    for mode in ["--publish-ai13-only", "--publish-nm25-only"]:
        subprocess.run(
            [sys.executable, "scripts/generate_semantic_contract_assets.py", mode],
            cwd=ROOT,
            check=True,
        )
        assert before == {p: p.read_bytes() for p in targets}
    for relative, blob in HISTORICAL_GIT_BLOBS.items():
        b = (ROOT / relative).read_bytes()
        assert (
            hashlib.sha1(b"blob " + str(len(b)).encode("ascii") + b"\0" + b).hexdigest() == blob
        ), relative
