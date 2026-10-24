"""AI 1.4 authority qualification, never materialization execution conformance."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import (
    SemanticContractVersion,
    get_semantic_contract,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from scripts import qualify_ai14_publication as publication
from scripts.generate_semantic_contract_assets import discovered_dependencies

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "contracts/architecture-interpretation/v1.4"
PREFIX = publication.PREFIX
CATALOG = publication.CATALOG
SCF = "scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7"


# Raw-byte fixtures for this publication and its exact historical authorities.
# New versions and runtime files are deliberately outside this closed inventory.
IMMUTABLE_SHA256: dict[str, str] = {
    "contracts/architecture-interpretation/v1.4/contract.json": "fb359160f19b07613816b94947fcd392ad92b23172564818def89900b0949812",
    "contracts/architecture-interpretation/v1.4/resources/conformance.json": "0044707e8209f5b412f8b5ee0bd0a6af23a883de500274ba09142d4fe07710bf",
    "contracts/architecture-interpretation/v1.4/resources/conformance.schema.json": "f7e603602b3c76ef9d9c43e1adebf98d0e23b3d61e7729be1ba7c95f30142397",
    "contracts/architecture-interpretation/v1.4/resources/required-output-derivations.json": "8d627a76f9b323bf9c488199ab498b441a78846fb302dbd8f5425b4ca54fa2f5",
    "contracts/architecture-interpretation/v1.4/resources/required-output-derivations.schema.json": "dfd95fbb09b9a05963853a7855b1e54374acfe7f42b2930350088434cbd508ff",
    "contracts/architecture-interpretation/v1.4/resources/rules.json": "bb76e06451d516cefc39f5d668ebf39a6934c3fc75b2d018b17343a721450161",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.3.json": "57dbf49ad26dc3a94aaca5aa502af8099fa89e8373ac9f4f2118af253526d4b1",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.4.json": "fb359160f19b07613816b94947fcd392ad92b23172564818def89900b0949812",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.3.json": "fdb5d13e1e6d83da2aaadcd40211bcd33be9e550d178a85ad071b58ed99b6124",
    "contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json": "e465444fec27cb5a43efbdb96f502025d31755be5ed5ed8c16329d699d859a85",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-conformance.json": "d5518ca8d18264fe21fb69cee39590d8e5bfa22151dc31ba2016235b8ff3e2ce",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-conformance.schema.json": "591b79cb230284a7ef9f48591e8563d8e7cba332a53af3cd1b39d9c8f13aa0fa",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-contract.json": "b3f00596c164109098b9020964c1a9bfafc52b345e6024941cb0bf50d3d3d6c5",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-detached-context.json": "0c713f4b90ccb60f397f6506e702da110cc5567cf0b05fd9f6fd8759a7ed7e8f",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-field-dispositions-1.7-to-2.4.json": "d83bbccd0e2baca895063404fe632f058174dd8adeab2b4fc0a1d9eb51e1ddf4",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-field-dispositions.schema.json": "9bb2e9195c12fee0120df40b60ed6b926601f88824a621b4b7e5885b92f931c1",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-legacy-compatibility.json": "39a99cb149ebdbd553d3d21c190163bc2ade06b6b482da2090a96c4a902fe54c",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-rules.json": "d3c6dd118e0cffa63c5344cc62361f057b4ca0f58503effc12a5481770e9c5f5",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-source-decoding-1.7.json": "df71b391ea494a37075ff910386a2017580db9388c376cab7479903552fa09a1",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.2-source-mapping-1.7-to-2.4.json": "67ff7cde821eb22fc148861a1d42fcd83a7260e92ebc4abdfe72f040521020ef",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-conformance.json": "8b900f2368e671f1ca7b244824d9670e54b21dbb504c30feac28d572a4bf2a6d",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-conformance.schema.json": "bda546aab23ed4ae8168347bc06156c8180ab27f77a3a20cce917328af2071d2",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-contextual-facts.json": "e83c06b55390263175d5c78374c89b1d76ef61c1fbac75b02122d2fee73850e0",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-contextual-facts.schema.json": "7aa7756ffa78b889ff11d2f2a4ac23bdaeb985f72bac547d02b786c50b3ee66d",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-detached-context.json": "d4ce3f866cf8864eb22fc8aff5ffa004cef4937b0b9a5b129ea81f43e95b3171",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-field-dispositions-1.7-to-2.5.json": "c43842da3df211bf44207c530b017ab67f8d70dc6e9ddf7241491346ba2d24ec",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-field-dispositions.schema.json": "50f27a675cc35d1d35a355982978f17e7148e1020f890879a3eb7d3795759d51",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-lifecycle-ownership.json": "da6a81329f483f471f60ed9603ddbb5586def21ba621083dab99c4c45475bb82",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-lifecycle-ownership.schema.json": "ea5066ecf7acac6d76f5c1f33b7c08941b936e8376ed22f769b25f488d32dc1d",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-lifecycle-provenance.schema.json": "62996e45e591cdc0c8d2a28641f3c200c07fbe0786a4c471c51ed539f3d178eb",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-rules.json": "65bc68ef65fc06290faf67ef402429ef3cf63bc47d96c9ee247e8d91c6a74504",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-source-mapping-1.7-to-2.5.json": "1723105d0aa0c286da55d1cae925d3daa6fcdd54a2cb347624ed8d14dcba072d",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-source-decoding-1.5.json": "026cc5e40d011a9928c3fba20f84851fd5d64e951627ad851d69033c98e39e61",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-source-decoding-1.6.json": "004bace3f3f05c7a97556ed6fab34a094e749de44e8c728c9686d36d709ac4fa",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-source-mapping-1.5-to-2.3.json": "e140efc81dded6488f0a27f59e87dac8b24dc21bc03060403945706ed10a6590",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-source-mapping-1.6-to-2.3.json": "466c4554c9ad0545ee0e9256e955e24844d16b37bbbc11b26154b2705f7fe85f",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-common.schema.json": "4800f0c5145cf22c62fd8bcd7037cda8d14ad857c13ee879c7b03bdde70218fb",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-logical.schema.json": "7f1d8a833502db21ef2348cd0a843686c67b54f96d1532cf7c07a2d7fa73340f",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-physical-base.schema.json": "50733ed51dd5c5ecd9fbe150b87ee88fb84c273ff16ee56878be66b7262a6f8c",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-physical-component.schema.json": "fcadb0f6a2bfaf6801c540045cd69cb435be38d68552575ebe2b251f3667951c",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-adr-physical-system.schema.json": "347cb9dfad02a054f9a54d7da8cea1ffc40d5931cd2b4a555614a05a057f91b1",
    "contracts/semantic-contract/v1.0/resources/authoring-1.5-schema-types.schema.json": "8a5fb427aad840157599727adab3a948eb88ec9c2a796f8dee41a5951e39c3b3",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-common.schema.json": "6f4d8d0ea8091aa3168e242fe15b973ce301e8c203348eec8cf43ee12932a298",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-logical.schema.json": "3e96f1c3153f541573fe4cf5dd9942db877ed97b9c34a3da6e589b6d60417fbf",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-physical-base.schema.json": "5e146831519ff469fdbee5b2da65bdc0067ea6b6d413b7b98e3fb948dc380fe8",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-physical-component.schema.json": "5fe8d5da0d381774d6d74b14691bb9fa47567d56ee733465eaa06c0d10f7bdb9",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-adr-physical-system.schema.json": "86891426608b68f947fa36016a9cd08da697b0db3a770ee06ecd4be50e63a7a3",
    "contracts/semantic-contract/v1.0/resources/authoring-1.6-schema-types.schema.json": "f27df797e88b76956fa4866535133a496e9d65aaedae600e19588deb3a96b16a",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-common.schema.json": "f3c31fa273b6c17eb805a5ddabc2a6d51656e724d4d4ab1193f85a0c12735777",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-logical.schema.json": "5ebcb3ed2b1959cbb9e448fd772b989c9108b6a31c68b327835a1cee95ca7566",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-physical-base.schema.json": "8e34b19d733bb019400a328c753fbb1da27f124ad3d56a1cbcec052883fa3ce5",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-physical-component.schema.json": "021c2e5b443f43c2973c0988a623978d64b8843a9570238db296441fc7260628",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-adr-physical-system.schema.json": "bf9e6f86e84af1b15e20bd3daee53930d01caccbb49c21eae08a68de754e42d6",
    "contracts/semantic-contract/v1.0/resources/authoring-1.7-schema-types.schema.json": "3791dbabc32070e4b3cec3ce49934583888e84308076b2fad9603518c276650a",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.0-conformance.json": "2b88de11e8d4cd8bea7e2c27a2edc781a20663a335cc38c6e2b4f29dd182df67",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.0-contract.json": "81df32e4044fc92937b1bb812ee1d9259f290b938be29e868d0597eee30ec1f1",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.0-rules.json": "e70191c3386224d68279e3c355baf10049463f83f3d1981936eb16fd76ecf7ad",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-compatibility.json": "b1f917e741c7fc081d471c97729146016e3563f4bf93abd04e8e0f3eb9b73434",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-conformance.json": "725e55a808d4f1e5eb0819928d67d58fa02e586237587a53b44a6f8af798c86e",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-conformance.schema.json": "16a8b7f94341fb72ee6c643c68971f2ee4fc538471b0d655e0fd88046af617e4",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-contract.json": "02f938ea53e76b83a83d9319029e09a4055d9c75da4b6955f0a80dd72fce836a",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-ledger.schema.json": "4d0caa154c61ceca80b0da504ae368f130461e4fe445a07c46d7e156388f50ec",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-rules.json": "6ea14c2eed67804e763dac7a6ab9232648d416e582826a70d2a7c2e0b61757ac",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.1-schema.json": "c37c5206dce55e14e1f3d56a8c90a3ce4b6d4b720870b27ac31986c447d45208",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-compatibility.json": "3c2ab4b284ad78a154782b04653977994c0e9a4bf58ed5fd8ea7f70f33647402",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-composition-bindings.json": "0b8c8d1d37664e4e36cc0fc703c5cea13db4cd4294b0bfb48ed2743f4aa9adb8",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-composition-bindings.schema.json": "e15c843f4b27c0df1d69668f1335bd79f0ba54548beb79baa25bc273cc91456e",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-conformance.json": "8d9268252dc7dcfbe3971dc804bd265990aa64249bc09c87796f9f2f69e27c8a",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-conformance.schema.json": "7550726ca21de1d9155c6eaf3f64ba205115433ac55524c61cfb4ced3885f17a",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-rules.json": "e79f487155f96627563ae1156b0ffa6d9b6b5fe8ce1f098114300da2c80ce292",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.2-schema.json": "79e705ecf53f9c8834a5ea1708d08be72f12f670fc43eace1c7b9ef14606175c",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.3-compatibility.json": "0b3b804485701d15129e5f2d066b4d7b742af310cb0591c8547c1f5f704adc79",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.3-composition-bindings.json": "13fd345692882869f2a9bfe26de1130bfc6d3913b3c4e3f85e1de8b0f5bcd843",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.3-composition-bindings.schema.json": "164a9b9342576fcf7c0c88a393e5ffaaa49c98872b68ac8d74fa13fa5280b4ea",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.3-conformance.json": "1e88e9107f22b9ffbad3efa1c3c23c87adb11413daf8aa13bc302d227bee3029",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.3-conformance.schema.json": "2d5cadf66d628585d6c6d45ea56815bb5efb2b4dc959d57100424c0f09837a12",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.3-ledger.schema.json": "2153ab360266d9f54796bdcf45e47b85b02d45c7ee6d0a6d27e514fd159b3efa",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.3-rules.json": "bce1c686b98b695c28827a753560be084d60ca0ea8a07a84c297d24eb8bb52d7",
    "contracts/semantic-contract/v1.0/resources/authoring-construction-1.3-schema.json": "c774668f24fc032d6c313141619c3d4a58c1a0fbd2f819ff45a0376db45d08db",
    "contracts/semantic-contract/v1.0/resources/authoring-domain-1.1-contract.json": "082d6c63211f2611e85d38fe7b674180c8c8276859d56b010830c6c381d01c6f",
    "contracts/semantic-contract/v1.0/resources/authoring-domain-1.1-schema.json": "766d8bd3c29de24d9163dd216b5e6a5dc4e7ab052b70828491c6bf03114ec2f9",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-conformance.json": "7df4c32e355fd4d77145bd07a7d2cc04ca0022a324b42b24191e930b6cb1f94b",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-contract.json": "9669f12be495c944d0f53fabd1004fbf49387dafe63618dcc64fc5bf0c6a4060",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-schema.json": "6ee9cb18c64975b1c72507b34cb76dde9f7e58e9310ceb285ab697d2683d7caf",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-architecture-model.schema.json": "0a85eaf60a128a0d09d16cc83c98c7d1c236783bed86a19cae87a20a8935ad3b",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-entity-registry.schema.json": "62bc9f42a0fc67edf6bec9dbdfb0499c0fcfe7f6f031a884855c544cc6909cef",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-entity.schema.json": "ba7bdd180a2f2ca838f885415c790a67cfd720c34779f4ef07e3eeaf062ee819",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-relationship-record.schema.json": "af36fc51822e3998e8ac2c1f17be8245470feea874862f177dd536cfd9fdf658",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-relationship-registry.schema.json": "3702cd68fa5a5acb74da804c7acde55840fd338c792b7e8f261721490a4fc51d",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-unresolved-registry.schema.json": "13461e3ec17069312e39063e4bf921ddebb0635d17f86640622143a1de5057b4",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-architecture-model.schema.json": "d7fe9ea9cc6a7d67d52b4190cc47f331a738bd85cddace147c6d7504f7a19df0",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-entity-registry.schema.json": "8c82185dba5cd2692830252cef497b54a94c61c089e00f1edb12cd355da7bc1f",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-entity.schema.json": "4ee0ee77dbc7746f60c33f85c2ccc10ae4fbc1f419e5955b0b449e179581497d",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-relationship-record.schema.json": "517edc9218c18aae0a51418ede7af086c692e13bc16365152e9ab038863ab0c4",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-relationship-registry.schema.json": "a27b5e95ac1abebe01f27f14037df0127b06c36e0dfed37268f1d82bc8ee9390",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-unresolved-registry.schema.json": "ed54fa1446343e5b5100f2e6fb45742c6768781cef97893a41b7245ebc8d757a",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-conformance.json": "49c9ee5614e601aee56f65cca17549b0046b43e0fa837962c2f9207e00e5d82c",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-normalized-architecture-model.schema.json": "6e61d23e8a1c0722727b8fe50ae915299fd310dab3cd1ae183a0435cd234d35b",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-normalized-entity-registry.schema.json": "972a7264b0830508c3627ee77aec12b13a174a28e5292fa9981aca5bc906ade7",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-normalized-entity.schema.json": "0a44d2119b082ec622461e4f7d71d54143be8d79e0f1985a677feaa0f7bbc162",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-relationship-record.schema.json": "f38a36b1d0ad419c47b40b3924fa743a47e44403fd93e2e0ee4059c9e7d3c1e9",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-relationship-registry.schema.json": "c9a5b6adcc0e109fa22ad674c94ec04912016b00dad02ba891902cbc5d152149",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-schema-unresolved-registry.schema.json": "0e46627fc741581e5fc218ce235b68d9981085b88cea0ac6c6893eb0e3d31919",
    "schema/authoring/v1.5/adr-common.schema.json": "4800f0c5145cf22c62fd8bcd7037cda8d14ad857c13ee879c7b03bdde70218fb",
    "schema/authoring/v1.5/adr-logical.schema.json": "7f1d8a833502db21ef2348cd0a843686c67b54f96d1532cf7c07a2d7fa73340f",
    "schema/authoring/v1.5/adr-physical-base.schema.json": "50733ed51dd5c5ecd9fbe150b87ee88fb84c273ff16ee56878be66b7262a6f8c",
    "schema/authoring/v1.5/adr-physical-component.schema.json": "fcadb0f6a2bfaf6801c540045cd69cb435be38d68552575ebe2b251f3667951c",
    "schema/authoring/v1.5/adr-physical-system.schema.json": "347cb9dfad02a054f9a54d7da8cea1ffc40d5931cd2b4a555614a05a057f91b1",
    "schema/authoring/v1.5/types.schema.json": "8a5fb427aad840157599727adab3a948eb88ec9c2a796f8dee41a5951e39c3b3",
    "schema/authoring/v1.6/adr-common.schema.json": "6f4d8d0ea8091aa3168e242fe15b973ce301e8c203348eec8cf43ee12932a298",
    "schema/authoring/v1.6/adr-logical.schema.json": "3e96f1c3153f541573fe4cf5dd9942db877ed97b9c34a3da6e589b6d60417fbf",
    "schema/authoring/v1.6/adr-physical-base.schema.json": "5e146831519ff469fdbee5b2da65bdc0067ea6b6d413b7b98e3fb948dc380fe8",
    "schema/authoring/v1.6/adr-physical-component.schema.json": "5fe8d5da0d381774d6d74b14691bb9fa47567d56ee733465eaa06c0d10f7bdb9",
    "schema/authoring/v1.6/adr-physical-system.schema.json": "86891426608b68f947fa36016a9cd08da697b0db3a770ee06ecd4be50e63a7a3",
    "schema/authoring/v1.6/types.schema.json": "f27df797e88b76956fa4866535133a496e9d65aaedae600e19588deb3a96b16a",
    "schema/authoring/v1.7/adr-common.schema.json": "f3c31fa273b6c17eb805a5ddabc2a6d51656e724d4d4ab1193f85a0c12735777",
    "schema/authoring/v1.7/adr-logical.schema.json": "5ebcb3ed2b1959cbb9e448fd772b989c9108b6a31c68b327835a1cee95ca7566",
    "schema/authoring/v1.7/adr-physical-base.schema.json": "8e34b19d733bb019400a328c753fbb1da27f124ad3d56a1cbcec052883fa3ce5",
    "schema/authoring/v1.7/adr-physical-component.schema.json": "021c2e5b443f43c2973c0988a623978d64b8843a9570238db296441fc7260628",
    "schema/authoring/v1.7/adr-physical-system.schema.json": "bf9e6f86e84af1b15e20bd3daee53930d01caccbb49c21eae08a68de754e42d6",
    "schema/authoring/v1.7/types.schema.json": "3791dbabc32070e4b3cec3ce49934583888e84308076b2fad9603518c276650a",
    "schema/normalized-model/v2.3/normalized-architecture-model.schema.json": "0a85eaf60a128a0d09d16cc83c98c7d1c236783bed86a19cae87a20a8935ad3b",
    "schema/normalized-model/v2.3/normalized-entity-registry.schema.json": "62bc9f42a0fc67edf6bec9dbdfb0499c0fcfe7f6f031a884855c544cc6909cef",
    "schema/normalized-model/v2.3/normalized-entity.schema.json": "ba7bdd180a2f2ca838f885415c790a67cfd720c34779f4ef07e3eeaf062ee819",
    "schema/normalized-model/v2.3/relationship-record.schema.json": "af36fc51822e3998e8ac2c1f17be8245470feea874862f177dd536cfd9fdf658",
    "schema/normalized-model/v2.3/relationship-registry.schema.json": "3702cd68fa5a5acb74da804c7acde55840fd338c792b7e8f261721490a4fc51d",
    "schema/normalized-model/v2.3/unresolved-registry.schema.json": "13461e3ec17069312e39063e4bf921ddebb0635d17f86640622143a1de5057b4",
    "schema/normalized-model/v2.4/normalized-architecture-model.schema.json": "d7fe9ea9cc6a7d67d52b4190cc47f331a738bd85cddace147c6d7504f7a19df0",
    "schema/normalized-model/v2.4/normalized-entity-registry.schema.json": "8c82185dba5cd2692830252cef497b54a94c61c089e00f1edb12cd355da7bc1f",
    "schema/normalized-model/v2.4/normalized-entity.schema.json": "4ee0ee77dbc7746f60c33f85c2ccc10ae4fbc1f419e5955b0b449e179581497d",
    "schema/normalized-model/v2.4/relationship-record.schema.json": "517edc9218c18aae0a51418ede7af086c692e13bc16365152e9ab038863ab0c4",
    "schema/normalized-model/v2.4/relationship-registry.schema.json": "a27b5e95ac1abebe01f27f14037df0127b06c36e0dfed37268f1d82bc8ee9390",
    "schema/normalized-model/v2.4/unresolved-registry.schema.json": "ed54fa1446343e5b5100f2e6fb45742c6768781cef97893a41b7245ebc8d757a",
    "schema/normalized-model/v2.5/normalized-architecture-model.schema.json": "6e61d23e8a1c0722727b8fe50ae915299fd310dab3cd1ae183a0435cd234d35b",
    "schema/normalized-model/v2.5/normalized-entity-registry.schema.json": "972a7264b0830508c3627ee77aec12b13a174a28e5292fa9981aca5bc906ade7",
    "schema/normalized-model/v2.5/normalized-entity.schema.json": "0a44d2119b082ec622461e4f7d71d54143be8d79e0f1985a677feaa0f7bbc162",
    "schema/normalized-model/v2.5/relationship-record.schema.json": "f38a36b1d0ad419c47b40b3924fa743a47e44403fd93e2e0ee4059c9e7d3c1e9",
    "schema/normalized-model/v2.5/relationship-registry.schema.json": "c9a5b6adcc0e109fa22ad674c94ec04912016b00dad02ba891902cbc5d152149",
    "schema/normalized-model/v2.5/unresolved-registry.schema.json": "0e46627fc741581e5fc218ce235b68d9981085b88cea0ac6c6893eb0e3d31919",
}


def resource(name: str) -> Any:
    return json.loads((CANONICAL / "resources" / (name + ".json")).read_text(encoding="utf-8"))


def matrix() -> list[dict[str, str]]:
    path = next((ROOT / "adrs/logical").glob("ADR-L-0038-*.yaml"))
    adr = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert adr["status"] == "accepted"
    text = next(row["rationale"] for row in adr["decisions"] if row["alias_id"] == "DEC-9011")
    return yaml.safe_load(text.split("```yaml\n")[1].split("```", 1)[0])


@pytest.fixture
def snapshot(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A fresh in-memory publication snapshot per mutation; no cached trust."""
    originals = publication.read
    values = {PREFIX + name: resource(name) for name in publication.NAMES}

    @lru_cache(maxsize=None)
    def read(root: Path, key: str) -> Any:
        return values[key] if key in values else originals(root, key)

    monkeypatch.setattr(publication, "read", read)
    return values


def test_independent_publication_qualification(snapshot: dict[str, Any]) -> None:
    assert publication.qualify(ROOT) == {
        "semantic_types": 27,
        "output_accounting": {"QUALIFIED": 186, "BLOCKED": 269},
        "complete_interpretation": "Unavailable",
        "runtime_execution": False,
    }


def test_all_types_and_label_selectors_match_accepted_authority() -> None:
    catalog = resource(CATALOG)
    types = {row["semantic_type"]: row for row in catalog["types"]}
    assert len(types) == 27
    oracle = {
        case["semantic_type"]: case["fixture"]
        for case in resource("conformance")["cases"]
        if case["category"] == "label_policy"
    }
    assert len(oracle) == 18
    for policy in matrix():
        row = types[policy["semantic_type"]]
        if policy["name"] == "not-applicable":
            assert not any(
                entry["destination"] in {"/name", "/summary"} for entry in row["outputs"]
            )
            continue
        for destination in ("name", "summary"):
            mode, field = policy[destination].split(":")
            assert oracle[row["semantic_type"]][destination] == {
                "mode": "authored" if mode == "A" else "representation",
                "source_field": field,
            }
            selected = next(
                entry for entry in row["outputs"] if entry["destination"] == "/" + destination
            )
            assert selected["status"] == "QUALIFIED"
            assert selected["producer"]["kind"] == (
                "field_placement" if mode == "A" else "literal_string_copy"
            )
            if mode == "R":
                assert selected["producer"]["source_field"] == field
                assert selected["classification"] == "representation_only"
    assert (
        Counter(
            row["producer"]["kind"]
            for ty in types.values()
            for row in ty["outputs"]
            if row["status"] == "QUALIFIED"
        )["literal_string_copy"]
        == 26
    )


@pytest.mark.parametrize("ty", [row["semantic_type"] for row in resource(CATALOG)["types"]])
def test_every_type_has_independent_branch_and_output_accounting(ty: str) -> None:
    catalog = resource(CATALOG)
    row = next(row for row in catalog["types"] if row["semantic_type"] == ty)
    assert row["root_permission"] == "catalog_membership_does_not_authorize_independent_root"
    paths = [entry["destination"] for entry in row["outputs"]]
    assert len(paths) == len(set(paths))
    for entry in row["outputs"]:
        if entry["status"] == "BLOCKED":
            assert "producer" not in entry
            assert entry["blocked"]["allows_complete_materialization"] is False
            assert entry["blocked"]["code"] in catalog["blockers"]
        else:
            assert "producer" in entry and "blocked" not in entry
    assert (
        len(
            [
                case
                for case in resource("conformance")["cases"]
                if case["semantic_type"] == ty and case["category"] == "output_coverage"
            ]
        )
        == 1
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing_type",
        "duplicate_type",
        "missing_required",
        "competing_producer",
        "wrong_source",
        "wrong_destination",
        "wrong_digest",
        "wrong_rule",
        "unknown_operation",
        "wrong_input",
        "changed_label",
        "missing_field_inventory",
        "semantic_as_ceremony",
        "missing_owner",
        "wrong_owner",
        "forged_producer",
        "wrong_branch",
        "missing_conditional",
        "broken_reference",
        "open_schema",
        "extra_proof",
        "unfrozen_conformance_id",
        "runtime_claim",
        "changed_inheritance",
        "missing_semantic_extensions",
        "blocked_known_identity",
        "wrong_destination_schema",
        "missing_nested_requirement",
        "wrong_applicability",
        "external_schema_ref",
        "invalid_schema_dialect",
    ],
)
def test_negative_publication_mutations_fail_closed(snapshot: dict[str, Any], fault: str) -> None:
    catalog = snapshot[PREFIX + CATALOG]
    first = catalog["types"][0]
    literal = next(
        entry
        for row in catalog["types"]
        for entry in row["outputs"]
        if entry.get("producer", {}).get("kind") == "literal_string_copy"
    )
    if fault == "missing_type":
        catalog["types"].pop()
    elif fault == "duplicate_type":
        catalog["types"][-1] = copy.deepcopy(first)
    elif fault == "missing_required":
        first["outputs"] = [entry for entry in first["outputs"] if entry["destination"] != "/id"]
    elif fault == "competing_producer":
        first["outputs"].append(copy.deepcopy(first["outputs"][0]))
    elif fault == "wrong_source":
        first["source_schema"]["schema_pointer"] = "/missing"
    elif fault == "wrong_destination":
        literal["destination"] = "/wrong"
    elif fault == "wrong_digest":
        literal["producer"]["inputs"][0]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "wrong_rule":
        literal["producer"]["rule_id"] = "forged-rule"
    elif fault == "unknown_operation":
        literal["producer"]["rule"] = {"local_rule": "truncate"}
    elif fault == "wrong_input":
        literal["producer"]["inputs"][0]["schema_pointer"] = "/properties/id"
    elif fault == "changed_label":
        literal["producer"]["source_field"] = "title"
    elif fault == "missing_field_inventory":
        entry = next(
            entry
            for row in catalog["types"]
            for entry in row["outputs"]
            if entry.get("producer", {}).get("kind") == "field_inventory"
        )
        entry["producer"]["inputs"].pop()
    elif fault == "semantic_as_ceremony":
        entry = next(
            entry
            for entry in first["outputs"]
            if entry.get("producer", {}).get("kind") == "field_placement"
        )
        entry["classification"] = "representation_only"
    elif fault in {"missing_owner", "wrong_owner"}:
        entry = next(
            entry
            for row in catalog["types"]
            for entry in row["outputs"]
            if entry.get("producer", {}).get("kind") == "contextual_rule"
        )
        if fault == "missing_owner":
            entry["prerequisites"] = []
        else:
            entry["producer"]["inputs"] = [
                publication.qualification(
                    ROOT, publication.BASE + "lifecycle-ownership", "/rows/16"
                )
            ]
    elif fault == "forged_producer":
        first["outputs"][0]["producer"] = copy.deepcopy(literal["producer"])
    elif fault == "wrong_branch":
        first["output_branch"] = "normative-proposition"
    elif fault == "missing_conditional":
        catalog["branches"][0]["requirements"].pop()
    elif fault == "broken_reference":
        first["source_schema"]["canonical_resource_key"] = "authoring/1.7/schema/missing"
    elif fault == "open_schema":
        snapshot[PREFIX + CATALOG + ".schema"]["additionalProperties"] = True
    elif fault == "extra_proof":
        first["outputs"][0]["proof_is_true"] = True
    elif fault == "unfrozen_conformance_id":
        snapshot[PREFIX + "conformance"]["cases"][1]["id"] = "AI14-001"
    elif fault == "runtime_claim":
        snapshot[PREFIX + "rules"]["public_boundary"]["execution"] = "implemented"
    elif fault == "changed_inheritance":
        snapshot[PREFIX + "rules"]["inherits"]["semantic_contract_fingerprint"] = (
            "scf:v1:sha256:" + "0" * 64
        )
    elif fault == "missing_semantic_extensions":
        first["outputs"] = [
            entry
            for entry in first["outputs"]
            if "{semantic_field_key}" not in entry["destination"]
        ]
    elif fault == "blocked_known_identity":
        entry = next(entry for entry in first["outputs"] if entry["destination"] == "/id")
        entry.pop("producer")
        entry["status"] = "BLOCKED"
        entry["blocked"] = copy.deepcopy(
            next(item["blocked"] for item in first["outputs"] if item["status"] == "BLOCKED")
        )
    elif fault == "wrong_destination_schema":
        literal["destination_schema"] = publication.qualification(
            ROOT, "normalized-model/2.5/schema/normalized-entity.schema", "/oneOf/1/properties/name"
        )
    elif fault == "missing_nested_requirement":
        entry = next(
            entry
            for row in catalog["types"]
            for entry in row["outputs"]
            if entry["required_subdestinations"]
        )
        entry["required_subdestinations"].pop()
    elif fault == "wrong_applicability":
        literal["applicability"]["output_branch"] = "canonical-relationship"
    elif fault == "external_schema_ref":
        snapshot[PREFIX + CATALOG + ".schema"]["$ref"] = "https://unqualified.invalid/schema.json"
    elif fault == "invalid_schema_dialect":
        snapshot[PREFIX + CATALOG + ".schema"]["$schema"] = "https://unqualified.invalid/dialect"
    with pytest.raises((publication.PublicationError, FileNotFoundError)):
        publication.qualify(ROOT, history=False)


def test_exact_fingerprint_closure_dependencies_and_package_bytes() -> None:
    contract = get_semantic_contract("architecture-interpretation", "1.4")
    wire = contract.to_wire()
    assert wire["semanticContractFingerprint"] == SCF
    assert len(contract.resource_manifest) == 60
    assert wire["frozenNormativeConformanceResources"] == [PREFIX + "conformance"]
    assert verify_semantic_contract(contract).success
    bundle = [
        {
            "canonicalResourceKey": entry.canonical_resource_key,
            "content": load_semantic_resource(entry.canonical_resource_key),
        }
        for entry in contract.resource_manifest
    ]
    assert validate_semantic_resource_closure(contract, bundle).closure_valid
    for entry in wire["resourceManifest"]:
        selected = load_semantic_resource(entry["canonicalResourceKey"])
        assert {
            dependency["canonicalResourceKey"] for dependency in entry["dependencies"]
        } == discovered_dependencies(entry["canonicalResourceKey"], selected)
    for name in publication.NAMES:
        data = (CANONICAL / "resources" / (name + ".json")).read_bytes()
        assert SCF.encode() not in data
        for directory in (
            "contracts/semantic-contract/v1.0/resources",
            "src/adr_kit/semantic_contract/v1_0/resources",
        ):
            assert (
                ROOT / directory / ("architecture-interpretation-1.4-" + name + ".json")
            ).read_bytes() == data
    for path in (
        "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.4.json",
        "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.4.json",
        "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.4.json",
    ):
        assert (ROOT / path).read_bytes() == (CANONICAL / "contract.json").read_bytes()
    for key in (
        PREFIX + "missing",
        PREFIX + "../1.3/rules",
        PREFIX + "required/output",
        "architecture-interpretation/99.99/rules",
    ):
        with pytest.raises(LookupError):
            load_semantic_resource(key)
    with pytest.raises(LookupError):
        get_semantic_contract("architecture-interpretation", "99.99")


@pytest.mark.parametrize("fault", ["missing", "modified", "extra", "fingerprint", "dependency"])
def test_closure_mutations(fault: str) -> None:
    contract = get_semantic_contract("architecture-interpretation", "1.4")
    wire = contract.to_wire()
    bundle = [
        {
            "canonicalResourceKey": entry.canonical_resource_key,
            "content": load_semantic_resource(entry.canonical_resource_key),
        }
        for entry in contract.resource_manifest
    ]
    if fault == "missing":
        bundle.pop()
    elif fault == "modified":
        bundle[0]["content"]["tampered"] = True
    elif fault == "extra":
        bundle.append(
            {"canonicalResourceKey": "architecture-interpretation/1.4/unqualified", "content": {}}
        )
    elif fault == "fingerprint":
        wire["semanticContractFingerprint"] = "scf:v1:sha256:" + "0" * 64
    elif fault == "dependency":
        wire["resourceManifest"][-1]["dependencies"] = [
            {"canonicalResourceKey": PREFIX + "rules", "contentDigest": "sha256:" + "0" * 64}
        ]
    assert not validate_semantic_resource_closure(
        SemanticContractVersion.from_wire(wire), bundle
    ).closure_valid


def assert_immutable_publication(root: Path) -> None:
    for relative, expected in IMMUTABLE_SHA256.items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative


def tracked_bytes(root: Path) -> dict[str, bytes]:
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    return {name: (root / name).read_bytes() for name in paths if name and (root / name).is_file()}


def test_deterministic_generation_preserves_existing_files() -> None:
    assert_immutable_publication(ROOT)
    # Snapshot the current tree, including future authorized successor/runtime
    # files. No historical Git baseline or perpetual changed-file allowlist.
    before = tracked_bytes(ROOT)
    for _ in range(2):
        subprocess.run(
            [sys.executable, "scripts/generate_semantic_contract_assets.py", "--publish-ai14-only"],
            cwd=ROOT,
            check=True,
        )
        assert tracked_bytes(ROOT) == before
        assert_immutable_publication(ROOT)
    publication.qualified_history(ROOT)


def test_future_acc14_file_does_not_invalidate_permanent_integrity(tmp_path: Path) -> None:
    for relative in IMMUTABLE_SHA256:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    assert_immutable_publication(tmp_path)
    # Only a foreign-version fixture, never publication of ACC 1.4 authority.
    successor = tmp_path / "contracts/authoring-construction/v1.4/resources/rules.json"
    successor.parent.mkdir(parents=True)
    successor.write_text(
        '{"fixture_only": true, "resource": "authoring-construction/1.4/rules"}', encoding="utf-8"
    )
    assert_immutable_publication(tmp_path)
    assert successor.is_file()
    historical = (
        tmp_path
        / "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-rules.json"
    )
    historical.write_bytes(historical.read_bytes() + b"\n")
    with pytest.raises(AssertionError, match="architecture-interpretation-1.3-rules"):
        assert_immutable_publication(tmp_path)


def test_historical_semantic_mutation_still_fails(snapshot: dict[str, Any]) -> None:
    value = publication.read(ROOT, publication.BASE + "rules")
    value["identity"]["canonical"] = "alias-derived"
    snapshot[publication.BASE + "rules"] = value
    with pytest.raises(
        publication.PublicationError, match="historical_resource_closure_unqualified"
    ):
        publication.qualified_history(ROOT)


def test_exact_integrity_is_independent_of_future_explicit_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import adr_kit.semantic_contract as contracts

    contract = get_semantic_contract("architecture-interpretation", "1.4")
    monkeypatch.setattr(contracts, "list_semantic_contracts", lambda: (contract,))
    assert contracts.list_semantic_contracts() == (contract,)
    test_exact_fingerprint_closure_dependencies_and_package_bytes()


def test_pr_boundary_policy_is_explicit_not_a_permanent_git_baseline() -> None:
    from tests.pr_scoped.qualify_ai14_publication import (
        validate_changed_paths,
        validate_cleanup_paths,
    )

    validate_changed_paths(["tests/test_architecture_interpretation_v14_publication.py"])
    with pytest.raises(ValueError, match="Outside PR #181 allowlist"):
        validate_changed_paths(["contracts/authoring-construction/v1.4/resources/rules.json"])
    validate_cleanup_paths(["packages/node/test/ai14-publication.test.mjs"])
    with pytest.raises(ValueError, match="non-test publication file"):
        validate_cleanup_paths(["contracts/architecture-interpretation/v1.4/contract.json"])


def test_frozen_oracle_and_blocker_register_are_honest() -> None:
    conf = resource("conformance")
    assert len(conf["cases"]) == 85
    assert conf["authority_only"] is True and conf["runtime_execution_coverage"] is False
    assert all(case["coverage"] == "authority_only_not_runtime_execution" for case in conf["cases"])
    catalog = resource(CATALOG)
    schema = resource(CATALOG + ".schema")
    assert not list(Draft202012Validator(schema).iter_errors(catalog))
    system = next(row for row in catalog["types"] if row["semantic_type"] == "entity/system")
    summary = next(row for row in system["outputs"] if row["destination"] == "/summary")
    assert summary["producer"]["source_field"] == "alias_name"
    assert "label_duplication_only_no_substantive_system_description" in summary["verification"]
    assert {
        "custom_lifecycle",
        "declaring_context",
        "fingerprint_preimage",
        "uri_recipe",
        "created_at_encoding",
        "relationship_envelope",
    }.issubset(catalog["blockers"])
    assert catalog["coverage"]["BLOCKED"] == "missing_prerequisite_not_a_producer_or_coverage"


def test_resource_delivery_permutations_do_not_change_qualification(
    snapshot: dict[str, Any],
) -> None:
    before = publication.qualify(ROOT, history=False)
    delivered = list(reversed(snapshot.items()))
    snapshot.clear()
    snapshot.update(delivered)
    assert publication.qualify(ROOT, history=False) == before
    contract = get_semantic_contract("architecture-interpretation", "1.4")
    bundle = [
        {
            "canonicalResourceKey": entry.canonical_resource_key,
            "content": load_semantic_resource(entry.canonical_resource_key),
        }
        for entry in reversed(contract.resource_manifest)
    ]
    assert validate_semantic_resource_closure(contract, bundle).closure_valid


def test_changed_catalog_bytes_cannot_reuse_an_old_resource_qualification(
    snapshot: dict[str, Any],
) -> None:
    snapshot[PREFIX + CATALOG]["types"].reverse()
    with pytest.raises(publication.PublicationError, match="qualification_mismatch"):
        publication.qualify(ROOT, history=False)


@pytest.mark.parametrize("key", ["authoring-construction/1.3/rules", PREFIX + "../rules"])
def test_valid_but_unselected_or_malformed_resource_conveys_no_authority(
    snapshot: dict[str, Any], key: str
) -> None:
    snapshot[PREFIX + CATALOG]["semanticDependencies"].append(key)
    with pytest.raises(publication.PublicationError, match="unselected_resource_has_no_authority"):
        publication.qualify(ROOT, history=False)


def test_exact_installed_wheel_discovery(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheels"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(wheel_dir),
            str(ROOT),
        ],
        check=True,
        capture_output=True,
    )
    wheel = next(wheel_dir.glob("*.whl"))
    installed = tmp_path / "installed"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(installed),
            str(wheel),
        ],
        check=True,
        capture_output=True,
    )
    code = """
import pathlib,sys
sys.path.insert(0,sys.argv[1])
import adr_kit
from adr_kit.semantic_contract import get_semantic_contract,load_semantic_resource,validate_semantic_resource_closure
assert pathlib.Path(adr_kit.__file__).is_relative_to(sys.argv[1])
c=get_semantic_contract('architecture-interpretation','1.4')
assert c.to_wire()['semanticContractFingerprint']==sys.argv[2]
assert validate_semantic_resource_closure(c,[{'canonicalResourceKey':e.canonical_resource_key,'content':load_semantic_resource(e.canonical_resource_key)} for e in c.resource_manifest]).closure_valid
"""
    checked = subprocess.run(
        [sys.executable, "-I", "-c", code, str(installed), SCF],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.parametrize("value", ["", "a" * 10000, "Étiquette / exact\nJSON", "literal-alias"])
def test_published_literal_operation_has_no_coercion_or_fallback(value: str) -> None:
    operation = resource(CATALOG)["operation"]
    assert operation["input_count"] == 1 and operation["input_type"] == "string"
    assert operation["formatting"] is False and operation["fallback"] is False
    publication.verify_label_fixture(
        ROOT,
        "adr/logical",
        {"title": "A title", "context": value},
        {"/name": "A title", "/summary": value},
    )
    with pytest.raises(publication.PublicationError, match="changed_representation"):
        publication.verify_label_fixture(
            ROOT,
            "adr/logical",
            {"title": "A title", "context": value},
            {"/name": "A title", "/summary": value + "!"},
        )


@pytest.mark.parametrize(
    "ty",
    [
        row["semantic_type"]
        for row in resource(CATALOG)["types"]
        if row["output_branch"] in {"regular", "normative-proposition"}
    ],
)
def test_type_scoped_literal_fixture_verification(ty: str) -> None:
    policy = next(row for row in matrix() if row["semantic_type"] == ty)
    authored = {policy[key].split(":")[1]: "valid-label" for key in ("name", "summary")}
    outputs = {"/" + key: authored[policy[key].split(":")[1]] for key in ("name", "summary")}
    publication.verify_label_fixture(ROOT, ty, authored, outputs)
    for destination in ("/name", "/summary"):
        changed = {**outputs, destination: "forged-output"}
        with pytest.raises(publication.PublicationError):
            publication.verify_label_fixture(ROOT, ty, authored, changed)
    for value in (None, 17, {}, [], False):
        invalid = {**authored, policy["name"].split(":")[1]: value}
        with pytest.raises(publication.PublicationError):
            publication.verify_label_fixture(ROOT, ty, invalid, outputs)
    with pytest.raises(publication.PublicationError, match="missing_label_input"):
        publication.verify_label_fixture(ROOT, ty, {}, outputs)
