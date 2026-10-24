"""AI 1.3 publication oracles, not interpretation execution conformance."""

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

from adr_kit.semantic_contract import (
    SemanticContractVersion,
    calculate_semantic_contract_fingerprint,
    get_semantic_contract,
    list_semantic_contracts,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from scripts import qualify_ai13_publication as publication

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "contracts/architecture-interpretation/v1.3"
ASSETS = ROOT / "contracts/semantic-contract/v1.0"
BUNDLED = ROOT / "src/adr_kit/semantic_contract/v1_0"
EXPECTED_SCF = "scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167"
UUID = "019109a0-b1c2-7def-8a00-112233445566"
HISTORICAL_SHA256: dict[str, str] = {
    "contracts/architecture-interpretation/v1.1/contract.json": "cd247ae436f1154cc20884c56709cb8d7fec28047edccf15c198e66c5ee104a5",
    "contracts/architecture-interpretation/v1.1/resources/conformance.json": "92b43e5998530d35a1153dd7bfb29ea151f8a7a8cb41eeb0633bd099eaa9a2bc",
    "contracts/architecture-interpretation/v1.1/resources/legacy-compatibility.json": "93220b51293b8cd483e0b80611b47c46f4f1fa040d3b951da98fc2cd748c9de1",
    "contracts/architecture-interpretation/v1.1/resources/rules.json": "6e41a7379f5564406c059a8eb4e9bfbf420fabc2c606273733baa9419fa2d5eb",
    "contracts/architecture-interpretation/v1.1/resources/source-decoding-1.7.json": "5f3ff45ba5a7f3e71ce27c9bd83c6d63b7fec0f01d67dc51710d7cdddf3a16d1",
    "contracts/architecture-interpretation/v1.1/resources/source-mapping-1.7-to-2.4.json": "e195805840a3c99f58c0d16c2526d44c1d818db4d3ba347c9180502dec1e4cda",
    "contracts/architecture-interpretation/v1.1/schema.json": "c452517f340ad72d1d014271d7ca694cd26e6daa2f582bede1ed496ab0d3cb79",
    "contracts/architecture-interpretation/v1.2/contract.json": "b3f00596c164109098b9020964c1a9bfafc52b345e6024941cb0bf50d3d3d6c5",
    "contracts/architecture-interpretation/v1.2/resources/conformance.json": "d5518ca8d18264fe21fb69cee39590d8e5bfa22151dc31ba2016235b8ff3e2ce",
    "contracts/architecture-interpretation/v1.2/resources/conformance.schema.json": "591b79cb230284a7ef9f48591e8563d8e7cba332a53af3cd1b39d9c8f13aa0fa",
    "contracts/architecture-interpretation/v1.2/resources/detached-context.json": "0c713f4b90ccb60f397f6506e702da110cc5567cf0b05fd9f6fd8759a7ed7e8f",
    "contracts/architecture-interpretation/v1.2/resources/field-dispositions-1.7-to-2.4.json": "d83bbccd0e2baca895063404fe632f058174dd8adeab2b4fc0a1d9eb51e1ddf4",
    "contracts/architecture-interpretation/v1.2/resources/field-dispositions.schema.json": "9bb2e9195c12fee0120df40b60ed6b926601f88824a621b4b7e5885b92f931c1",
    "contracts/architecture-interpretation/v1.2/resources/legacy-compatibility.json": "39a99cb149ebdbd553d3d21c190163bc2ade06b6b482da2090a96c4a902fe54c",
    "contracts/architecture-interpretation/v1.2/resources/rules.json": "d3c6dd118e0cffa63c5344cc62361f057b4ca0f58503effc12a5481770e9c5f5",
    "contracts/architecture-interpretation/v1.2/resources/source-decoding-1.7.json": "df71b391ea494a37075ff910386a2017580db9388c376cab7479903552fa09a1",
    "contracts/architecture-interpretation/v1.2/resources/source-mapping-1.7-to-2.4.json": "67ff7cde821eb22fc148861a1d42fcd83a7260e92ebc4abdfe72f040521020ef",
    "contracts/architecture-interpretation/v1.2/schema.json": "7351f4fde08968e3bb1108c45498ff01899cedf7e9cfb961e305c4391cdc5912",
    "contracts/architecture-ir/architecture-ir.schema.json": "78d2adb029f81354e675d4204b9071a405b24fe9e6a5b1ca30cf3b7cc57407ed",
    "contracts/authoring-construction/v1.0/contract.json": "81df32e4044fc92937b1bb812ee1d9259f290b938be29e868d0597eee30ec1f1",
    "contracts/authoring-construction/v1.0/resources/conformance.json": "2b88de11e8d4cd8bea7e2c27a2edc781a20663a335cc38c6e2b4f29dd182df67",
    "contracts/authoring-construction/v1.0/resources/rules.json": "e70191c3386224d68279e3c355baf10049463f83f3d1981936eb16fd76ecf7ad",
    "contracts/authoring-construction/v1.0/schema.json": "b3b16abf61027261222e1d53c4512df3083fbf8abde53e1456aa25ca03ff5dbb",
    "contracts/authoring-construction/v1.1/contract.json": "02f938ea53e76b83a83d9319029e09a4055d9c75da4b6955f0a80dd72fce836a",
    "contracts/authoring-construction/v1.1/resources/compatibility.json": "b1f917e741c7fc081d471c97729146016e3563f4bf93abd04e8e0f3eb9b73434",
    "contracts/authoring-construction/v1.1/resources/conformance.json": "725e55a808d4f1e5eb0819928d67d58fa02e586237587a53b44a6f8af798c86e",
    "contracts/authoring-construction/v1.1/resources/conformance.schema.json": "16a8b7f94341fb72ee6c643c68971f2ee4fc538471b0d655e0fd88046af617e4",
    "contracts/authoring-construction/v1.1/resources/ledger.schema.json": "4d0caa154c61ceca80b0da504ae368f130461e4fe445a07c46d7e156388f50ec",
    "contracts/authoring-construction/v1.1/resources/rules.json": "6ea14c2eed67804e763dac7a6ab9232648d416e582826a70d2a7c2e0b61757ac",
    "contracts/authoring-construction/v1.1/schema.json": "c37c5206dce55e14e1f3d56a8c90a3ce4b6d4b720870b27ac31986c447d45208",
    "contracts/authoring-construction/v1.2/contract.json": "5cfd8b8f9a50351316f9f92e498b96e9d09569c0da6d0b9dc9fa308fd2a6dc80",
    "contracts/authoring-construction/v1.2/resources/compatibility.json": "3c2ab4b284ad78a154782b04653977994c0e9a4bf58ed5fd8ea7f70f33647402",
    "contracts/authoring-construction/v1.2/resources/composition-bindings.json": "0b8c8d1d37664e4e36cc0fc703c5cea13db4cd4294b0bfb48ed2743f4aa9adb8",
    "contracts/authoring-construction/v1.2/resources/composition-bindings.schema.json": "e15c843f4b27c0df1d69668f1335bd79f0ba54548beb79baa25bc273cc91456e",
    "contracts/authoring-construction/v1.2/resources/conformance.json": "8d9268252dc7dcfbe3971dc804bd265990aa64249bc09c87796f9f2f69e27c8a",
    "contracts/authoring-construction/v1.2/resources/conformance.schema.json": "7550726ca21de1d9155c6eaf3f64ba205115433ac55524c61cfb4ced3885f17a",
    "contracts/authoring-construction/v1.2/resources/rules.json": "e79f487155f96627563ae1156b0ffa6d9b6b5fe8ce1f098114300da2c80ce292",
    "contracts/authoring-construction/v1.2/schema.json": "79e705ecf53f9c8834a5ea1708d08be72f12f670fc43eace1c7b9ef14606175c",
    "contracts/authoring-domain/v1.0/contract.json": "b2de54a60b6f395dfc69a8ddb1b9707def18e5c93456607f947fc0af5d473c6a",
    "contracts/authoring-domain/v1.0/schema.json": "805a3918ffe755b4468e72255bd70afece1a88ace0d1ef4e816277e257bb8d84",
    "contracts/authoring-domain/v1.1/contract.json": "082d6c63211f2611e85d38fe7b674180c8c8276859d56b010830c6c381d01c6f",
    "contracts/authoring-domain/v1.1/schema.json": "766d8bd3c29de24d9163dd216b5e6a5dc4e7ab052b70828491c6bf03114ec2f9",
    "contracts/compatibility/cli-behavior.json": "45cd05a1b8403c11ec444c939fa8c3f715925fb568c345f7edd4f24c2bda95e1",
    "contracts/compatibility/cli-surface.json": "ce6d29f7d08580ff9f9bcdb79a6aac38a935f6c421407e6ae7e26cf3bc857a89",
    "contracts/compatibility/host-capabilities.json": "43dd76f99b66a6b92a0e99c0997753d4d5248a57ae8cd8aae27e2b4247c73414",
    "contracts/compatibility/python-capabilities.json": "22e4bdbc7c6e6978f3c8ac0260dd0e30645f0f01ae9278bfda283f03441301c2",
    "contracts/compatibility/python-surface.json": "f10bbb785f5d8a412a72247899727e430a7ce280c35c854003636d2858a96087",
    "contracts/compatibility/typescript-surface.json": "53412f14fa64ffa28bf1dd1b7cd8039fc639c4e24c98b54538cb6bb734669b67",
    "contracts/conformance/consumer-binding-v1/authoring-discovery/authoring-discovery-v1.json": "fff486c791521f6244114fd00ce6f736c49a27474dc1f22283f406da94553017",
    "contracts/conformance/consumer-binding-v1/embodiment-linkage/evidence-v15.json": "c1529ee042a8ce22f2884ce75be45ac9d7da954ac97cf88aaf7fd3e89734ff35",
    "contracts/conformance/consumer-binding-v1/embodiment-linkage/evidence-v16-enforces-inferred.json": "c853888cbe627ab0c8c907f42fb06ceefe512fffce460a5d0971ef718de8aad6",
    "contracts/conformance/consumer-binding-v1/embodiment-linkage/evidence-v16.json": "ab8086539b1fb1eaee68fe141bf78efe230d32e477b2586d00d63c85e8990a0b",
    "contracts/conformance/consumer-binding-v1/manifest.json": "50c1fd4682e8e6c5d6cb24edddf68889e759d087067dbec914a01e2dd2cc771a",
    "contracts/conformance/consumer-binding-v1/relationships/canonical-and-compatibility.json": "34b2316949e89ad0d784eaae2b70184c4f555d3e7a4ea4711c63ff05760ee6ac",
    "contracts/conformance/consumer-binding-v1/repository/model-v21.json": "928786b5aa4230e905c1f8aa9ea1fb0b69a061ef059755ef0e2555186f73e804",
    "contracts/conformance/consumer-binding-v1/repository/unsupported-model.json": "4b9ce2ff61ab23e93e16224c53529d2155a546c9343c94a0364da2552309e1ee",
    "contracts/conformance/consumer-binding-v1/semantic-extensions/core-extension-invalid.json": "94ab491c9bc3cadbf1895c72492624bbac0a86c6b42b36e0576bcc79a3d78edb",
    "contracts/conformance/consumer-binding-v1/semantic-extensions/qualified-unknown.json": "9783d098acc861a4fdcd0b4461a8c73fcd7ed6d4a9bb0a0127b6b470a02fdb20",
    "contracts/conformance/consumer-binding-v1/unresolved/unresolved-first-class.json": "646698565da6d852ea493bdc281242232592765efeeb829df104d90317b53ebf",
    "contracts/custom-entity/registries/adrkit/registry.json": "06b76fccb1d66a37e854d71b3b44b89cb8406201e214ad63d55c5cd57331e5da",
    "contracts/custom-entity/v1.0/contract.json": "9669f12be495c944d0f53fabd1004fbf49387dafe63618dcc64fc5bf0c6a4060",
    "contracts/custom-entity/v1.0/schema.json": "6ee9cb18c64975b1c72507b34cb76dde9f7e58e9310ceb285ab697d2683d7caf",
    "contracts/custom-entity/v1.0/vectors/contract-fingerprint.json": "7df4c32e355fd4d77145bd07a7d2cc04ca0022a324b42b24191e930b6cb1f94b",
    "contracts/design-journal-promotion-contract/v0.1/conformance/01-valid-promotable-pre-lock.json": "db1082c3cfe746b6369257aa933e02e1b02f456722708bc9a79692e6e94bb004",
    "contracts/design-journal-promotion-contract/v0.1/conformance/02-valid-locked.json": "5bbe710c660400c4d62ba05a37ba0f02510f1057a09f4287a68db643b77153b3",
    "contracts/design-journal-promotion-contract/v0.1/conformance/03-non-promotable.json": "24ffcd952f464b5392e9169651114c1465f10788692cc88ad626f5f3cb5c36a1",
    "contracts/design-journal-promotion-contract/v0.1/conformance/04-unresolved-outcome-ref.json": "bd24556cfc96e82ffe7e2825d0d6b067cc2d0c8f98c55382e7a3077d2a8a37b9",
    "contracts/design-journal-promotion-contract/v0.1/conformance/05-duplicate-outcome-id.json": "b875ac4b898c9af92a1355dc834f01645cc88a9a3c80ee1761e7394fdb64257f",
    "contracts/design-journal-promotion-contract/v0.1/conformance/06-unmapped-promotion-required.json": "eaad3988a7ea6bf8a1fce8b3a27bdab58d69e54b30756e28ed797d4e41a30c88",
    "contracts/design-journal-promotion-contract/v0.1/conformance/07-blocker-with-mechanical-true.json": "183b761ffc1821fb81ea1dafe632962919a9438ac87b52a7f4255b708afdaf07",
    "contracts/design-journal-promotion-contract/v0.1/conformance/08-unbound-payload-ref.json": "f7828b8ccbfaca059e84c3d12df45be2360232b7cbcc4dbe7dd0add7bbf5609d",
    "contracts/design-journal-promotion-contract/v0.1/conformance/09-schema-binding-mismatch.json": "9a9ac0c1145f52cf5e819b29e492af29ca1c15d908362ad7413f88a158b76734",
    "contracts/design-journal-promotion-contract/v0.1/conformance/10-baseline-provider-mismatch.json": "f5ae523491cff8cfe1846a65029871b9fab58f3aa0adc1240a77fd65f4bb4d93",
    "contracts/design-journal-promotion-contract/v0.1/conformance/11-statement-change-invalidates.json": "567a4a2bdf075b03d7cabd684a645e680b27569b8a04b7b542282c4ab446ba94",
    "contracts/design-journal-promotion-contract/v0.1/conformance/12-mutation-change-invalidates.json": "c020e14473ee3e008f7c5ea07303b078594571284a01065752e2928b85c86c9f",
    "contracts/design-journal-promotion-contract/v0.1/conformance/13-multi-provider-unsupported.json": "bf3b15ee768b27b37e5a8c5d67bffb4edfa81f754c026ec48ee7a21379748cfb",
    "contracts/design-journal-promotion-contract/v0.1/conformance/14-class-d-retry.json": "33b9c13bdd8095ec96c7093c7b35c7bc87d50f05aac64436fb1c5538a4c919ed",
    "contracts/design-journal-promotion-contract/v0.1/schema.json": "81e18c34f7b6ca47a01e90efed2b156ec2716c0b16cbb553f388b049a7cc0377",
    "contracts/design-journal/v0.1/schema.json": "0f8bce1bbf176250839997e6937ac4d0765c7d999b4b72712c175f7c74634d0c",
    "contracts/semantic-contract/v1.0/catalog/semantic-contract-catalog-1.0.json": "44805f34c9785539d5edb8ab3b70d1add02f6365d75c4a9e2df156a03d7a9c34",
    "contracts/semantic-contract/v1.0/current/semantic-contract-current-1.0.json": "a56db66274fecf7442d314afdf1d183b0284b3ef56ae45381258ea8f1f9d7100",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.1.json": "f4682920485823f85bd77c78fcea0e34fb1d167ea854198b6228a9a2733c06e3",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.2.json": "b3f00596c164109098b9020964c1a9bfafc52b345e6024941cb0bf50d3d3d6c5",
    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation.json": "763c23e826e17898e40d0964a7848aa7bab930bf1140cc0e1c62300b952d5c6f",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.0.json": "81df32e4044fc92937b1bb812ee1d9259f290b938be29e868d0597eee30ec1f1",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.1.json": "02f938ea53e76b83a83d9319029e09a4055d9c75da4b6955f0a80dd72fce836a",
    "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.2.json": "5cfd8b8f9a50351316f9f92e498b96e9d09569c0da6d0b9dc9fa308fd2a6dc80",
    "contracts/semantic-contract/v1.0/definitions/normalized-model-2.4.json": "22d4f8523c691599303af64dbe259f59e97ae68d17ae09da5ac6ef677b91fde0",
    "contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json": "e465444fec27cb5a43efbdb96f502025d31755be5ed5ed8c16329d699d859a85",
    "contracts/semantic-contract/v1.0/definitions/normalized-model.json": "fea7398f854155933a414d327c4e08d97cbd469e8503f13558c12e426971bd50",
    "contracts/semantic-contract/v1.0/definitions/normative-semantics-1.0.json": "3682a5031b3232e1a7ff86af8101632336f2be67bb0795f1ca78076b61543430",
    "contracts/semantic-contract/v1.0/definitions/normative-semantics.json": "3682a5031b3232e1a7ff86af8101632336f2be67bb0795f1ca78076b61543430",
    "contracts/semantic-contract/v1.0/policy/semantic-contract-policy-1.0.json": "52d3aac6a8ca76958712e7a574d8f6ad654cf0edfe1dafd52a142a1c5bcc050a",
    "contracts/semantic-contract/v1.0/profiles/architecture-materialization-1.0.json": "2d1c324a3846ced1909e341d5e3b6ef59295d9f8df30b95888672f0388cd1597",
    "contracts/semantic-contract/v1.0/profiles/architecture-materialization-1.1.json": "ff33d9b8556a1c7b1b12f4b932d86ba6a9ebe0f3d8e34f2f2341f77b5b50b688",
    "contracts/semantic-contract/v1.0/qualifications/architecture-materialization-1.0.json": "e1d912bc509873bd6377f0de90bef805120978f03fd96aae680def444563c8c3",
    "contracts/semantic-contract/v1.0/qualifications/architecture-materialization-1.1.json": "d22c72a4109a5b7276469254ad781118830b37803c029ef992d24ba133a20a91",
    "contracts/semantic-contract/v1.0/resource-manifest-entry.schema.json": "bc6df72ffae3d096b93809e9de06a9e019488aa63610dd2bbad8803c59ecd582",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-conformance.json": "92b43e5998530d35a1153dd7bfb29ea151f8a7a8cb41eeb0633bd099eaa9a2bc",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-legacy-compatibility.json": "93220b51293b8cd483e0b80611b47c46f4f1fa040d3b951da98fc2cd748c9de1",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-rules.json": "6e41a7379f5564406c059a8eb4e9bfbf420fabc2c606273733baa9419fa2d5eb",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-source-decoding-1.7.json": "5f3ff45ba5a7f3e71ce27c9bd83c6d63b7fec0f01d67dc51710d7cdddf3a16d1",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-source-mapping-1.7-to-2.4.json": "e195805840a3c99f58c0d16c2526d44c1d818db4d3ba347c9180502dec1e4cda",
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
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-conformance.json": "718a7fc17405d9ce3c946f01348fd40ab6c3061d346c399928b03e7ea0e3770b",
    "contracts/semantic-contract/v1.0/resources/architecture-interpretation-rules.json": "ae6fe83091ac9da60e460163755fa67aae37303e7bdbebdd4889e38184dffe6b",
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
    "contracts/semantic-contract/v1.0/resources/authoring-domain-1.1-contract.json": "082d6c63211f2611e85d38fe7b674180c8c8276859d56b010830c6c381d01c6f",
    "contracts/semantic-contract/v1.0/resources/authoring-domain-1.1-schema.json": "766d8bd3c29de24d9163dd216b5e6a5dc4e7ab052b70828491c6bf03114ec2f9",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-conformance.json": "7df4c32e355fd4d77145bd07a7d2cc04ca0022a324b42b24191e930b6cb1f94b",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-contract.json": "9669f12be495c944d0f53fabd1004fbf49387dafe63618dcc64fc5bf0c6a4060",
    "contracts/semantic-contract/v1.0/resources/custom-entity-1.0-schema.json": "6ee9cb18c64975b1c72507b34cb76dde9f7e58e9310ceb285ab697d2683d7caf",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-conformance.json": "83b430f0fdd5cc2eb128dc197e97641f9e7a2f6afc7b0177f4b7b9bb5fe5b001",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-architecture-model.schema.json": "0a85eaf60a128a0d09d16cc83c98c7d1c236783bed86a19cae87a20a8935ad3b",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-entity-registry.schema.json": "62bc9f42a0fc67edf6bec9dbdfb0499c0fcfe7f6f031a884855c544cc6909cef",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-normalized-entity.schema.json": "ba7bdd180a2f2ca838f885415c790a67cfd720c34779f4ef07e3eeaf062ee819",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-relationship-record.schema.json": "af36fc51822e3998e8ac2c1f17be8245470feea874862f177dd536cfd9fdf658",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-relationship-registry.schema.json": "3702cd68fa5a5acb74da804c7acde55840fd338c792b7e8f261721490a4fc51d",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.3-schema-unresolved-registry.schema.json": "13461e3ec17069312e39063e4bf921ddebb0635d17f86640622143a1de5057b4",
    "contracts/semantic-contract/v1.0/resources/normalized-model-2.4-conformance.json": "7fe75c9ea6899aaf075a10b684a16a7f973ab3cf6df20d5459d1e31e31eccbf1",
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
    "contracts/semantic-contract/v1.0/resources/normative-semantics-conformance.json": "189049af5fa3612fda182ce9995fe8e6bde7fa921ed13a1072143e7fb123a170",
    "contracts/semantic-contract/v1.0/resources/normative-semantics-definition.json": "17a7909dd5de9da9cc7001aace0100da86942953e9c3010b212df410f6bebec5",
    "contracts/semantic-contract/v1.0/semantic-contract-assembly-request.schema.json": "b10e7382456dc00f33f9dd50576e5bda69b46b971f492df33eac74c7edfdf894",
    "contracts/semantic-contract/v1.0/semantic-contract-assembly-result.schema.json": "a336121eec1abf83a1fbe1d99de32e89e5b19c3bb005c5db284429b43b4582a0",
    "contracts/semantic-contract/v1.0/semantic-contract-catalog.schema.json": "21269bd3e327e893f7841522e953c0a4330d73b68cc171416dd33d4066c618c5",
    "contracts/semantic-contract/v1.0/semantic-contract-corpus-validation-request.schema.json": "e46b48cedf51b0767167b27093ee96ebb0615e5aae6bdf0179302a9b705920b0",
    "contracts/semantic-contract/v1.0/semantic-contract-corpus-validation-result.schema.json": "5a14c5fe769623cf47660e4651f4af6bad411dd7ebb78813932cd59abebaad5c",
    "contracts/semantic-contract/v1.0/semantic-contract-current-resolution-request.schema.json": "9577f1fd2f88c7a0ec98b076cdda202954ab1056b371dd2757bbb2400c9f23ce",
    "contracts/semantic-contract/v1.0/semantic-contract-current-resolution-result.schema.json": "f8819fca0b75ad86ef8a5ef668c87c605f6d35b1e0f2f303aef3bfa1d7a9abc8",
    "contracts/semantic-contract/v1.0/semantic-contract-current-selection.schema.json": "55802431060dbbf1c667927c1337971db4bf3df6aee2509321deeb477c889573",
    "contracts/semantic-contract/v1.0/semantic-contract-policy.schema.json": "e7e794780c58eb81d3bdd26fcac4a6ab4468a621985f84d4cda2a9da78116b96",
    "contracts/semantic-contract/v1.0/semantic-contract-profile.schema.json": "14f7784620c559ed1dbcb8cae2f5557a768413e94b16b773452af8fb2fcb67ee",
    "contracts/semantic-contract/v1.0/semantic-contract-qualification.schema.json": "71c70568311208c2549469cd8e44fec02f1a39a1ba364b0214c62ed25ded63f5",
    "contracts/semantic-contract/v1.0/semantic-contract-set.schema.json": "a3bcdf9978b840b7bb3235c0861c1ab8ed87fab0296f5c5ff1221d7d6539ff42",
    "contracts/semantic-contract/v1.0/semantic-contract-version.schema.json": "92056ccb9f7ca59ddb2d9d527e3ac8a09db8ad89c7607ce0baef34e1efde5a58",
    "contracts/semantic-contract/v1.0/sets/scs-v1-sha256-2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020.json": "500e6f8dbafefaa94272d2632bad34856d63a8c47b5b5f4331560bc0a54329f6",
    "contracts/semantic-contract/v1.0/sets/scs-v1-sha256-d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6.json": "35c419c4fdcfdf47b6d001672758a6a0b485f041425c9405f39548f05a1f9c4d",
    "contracts/semantic-core/v1.0/contract.json": "18ab2f2d349a15adcb7e8dee1db1474f744300c3d631c3d767e8e4cc9a5966ed",
    "contracts/semantic-core/v1.0/vectors/architecture-reference-validation.json": "8a69de8695a633c88d1b505ce999574e6f6a1c5f73f8bfbe5fb1c5ff9a83d716",
    "contracts/semantic-core/v1.0/vectors/architecture-validation.json": "c87919c8f6ad486762104fb39fb34d71d5722a1c9f653324c47f987eed42d834",
    "contracts/semantic-core/v1.0/vectors/attribution-shim-generation.json": "8854d5042fdef6fba6c576d78a4f1b597ba91eb906ad7de140207ae42f3fb928",
    "contracts/semantic-core/v1.0/vectors/contract-validation.json": "9d9d2581dcb07e0ef2499c316e02109422f0228a904ae005cf0ad9ceb76dbd69",
    "contracts/semantic-core/v1.0/vectors/embodiment-linkage.json": "cf0430b6b71abe59a6e0f4706f128a8b1c8d6d36cb508e13b1ccc322bc23be7b",
    "contracts/semantic-core/v1.0/vectors/generated-artifact-classification.json": "f059ea43c59422465138d0072f9892cba360b8a15eee48df6a2b8dca57a26d3d",
    "contracts/semantic-core/v1.0/vectors/project-metadata-validation.json": "c8723ec1110282b3c1d086eb072989f046d50cf56bbe0509e5937ff9963fb4c8",
    "contracts/semantic-core/v1.0/vectors/repository-validation.json": "f57ad3f8dbeb74ba1694e046768cd34f84c8e5e386c7662a407135034e0d012d",
    "contracts/semantic-core/v1.0/vectors/semantic-contract-set-governance.json": "a9fa1a63497e5f7da1ae3f6d80536c0d0bfbaed5b5be14ce6d36e815cd7b5734",
    "contracts/semantic-core/v1.0/vectors/semantic-contract.json": "9fce011f73f9fc5ac1c465b682aa896d993a8b6dcdeee908d165f946cfa583e5",
    "contracts/semantic-core/v1.1/contract.json": "42422571f948058c98d6f322c98424edb7c6ceafa7e64173cc0748961d2b460e",
    "contracts/semantic-core/v1.1/vectors/architecture-materialization.json": "396b238b863014e63202364bd36f25d2e6878756046d94958168c9e598680f85",
    "contracts/semantic-core/v1.2/contract.json": "7588fa387cb25e64288f2e962d01461f0823376672aac152a855f9cedccccf80",
    "contracts/semantic-core/v1.2/vectors/authoring-construction-transport.json": "5a4624fcac997c815cbfc16fcc7445936cc81555a0486b116337beead2251043",
    "contracts/semantic-core/v1.3/contract.json": "ce2fba984684e260ff383123be2649306672f4779dd18fb00ad3092f05272b12",
    "contracts/semantic-core/v1.4/contract.json": "a3433e0b925273ac0c220538aaaedb2879bb7d98d7aa2ae2dc78d1eb70c4eead",
    "contracts/semantic-core/v1.5/contract.json": "cf9e5c259b5dc62e176688d7609e42a0905f9f61c08b522a16de9971163d6e0c",
    "schema/architecture-discovery/v1.1/architecture-index.schema.json": "5a08df6f01a0a37a2fa681acb9b7828cb7720c7287d8367a4d0fadf7fb6e5e80",
    "schema/architecture-discovery/v1.1/entity-registry.schema.json": "98795b46e167affbd35c5415c9f7947d8784c273b918530376d22590d90a047b",
    "schema/authoring/v1.2/adr-common.schema.json": "a91a351c4e7c8ddf85c3395d366f1de9782fb1fdd89466dade5522567cd3d50c",
    "schema/authoring/v1.2/adr-logical.schema.json": "f8b62b44e19e03be6b8c17c6b9cbc8ae26cc0e59d5c50f1149abb8fcccd13ba1",
    "schema/authoring/v1.2/adr-physical-base.schema.json": "7be1399209bc7fac890786ff8807ed071d0e0aa90767c0129776a025b67a5d36",
    "schema/authoring/v1.2/adr-physical-component.schema.json": "93979efe12c8ba4e1d79b197ee1dbf1985bfc3523835c30592027bf2307c985d",
    "schema/authoring/v1.2/adr-physical-system.schema.json": "4ea0ca069bb0e8780c32947d3b8bbc32d91b3aff7b1b1b612298131bf61afc06",
    "schema/authoring/v1.2/adr-physical.schema.json": "6452e57d0d24381bf051e674e12fe96ca1c973aad72f531236cb67339f970533",
    "schema/authoring/v1.2/invariant.schema.json": "210cc15723c9e5437673991e3e4a0154fb3ca529adf032088924bdd7890b7deb",
    "schema/authoring/v1.2/types.schema.json": "6c433753a43c8dd279f5aec12e81b8876c9360a04db8d817bca10246f2a00f8a",
    "schema/authoring/v1.3/adr-common.schema.json": "a585ba26a5d1cb326d09f7e8da59d3a05a4bccac1aabe02b9a8d6b82bf5926e9",
    "schema/authoring/v1.3/adr-logical.schema.json": "fccec445b37f43458ccfc7d524d26fb3f609e8765089383c2beea9df802e22f0",
    "schema/authoring/v1.3/adr-physical-base.schema.json": "0360b15e07bb91639e3b382578e3116cacbc97f30ad7e0f7ff7b91803257083f",
    "schema/authoring/v1.3/adr-physical-component.schema.json": "e96fef221b66484b17993361618b6b219d6ed6a567f335948f068ae1f3ad31da",
    "schema/authoring/v1.3/adr-physical-system.schema.json": "86f0ceaa9c84ab64be908ce7f87b302db04ee12f842e69bc0126dde0f1ee5b09",
    "schema/authoring/v1.3/adr-physical.schema.json": "094d65d02cdd08cda70cb9e000326a9204bce73c7cbaae135225ec6568a669f4",
    "schema/authoring/v1.3/types.schema.json": "612d73a201177db340bbb8beab7abd83b1b940f9d262abe85bb4ea5457369816",
    "schema/authoring/v1.4/adr-common.schema.json": "8d80bf29c59b4e04e6dbe42b0ff2339ee16ce43c5228af71a409ece597a00c98",
    "schema/authoring/v1.4/adr-logical.schema.json": "c413604d70e8750f5f1d6f6b78dcc5e207a2756a603940dfc4a7eb719b757c50",
    "schema/authoring/v1.4/adr-physical-base.schema.json": "1ec099dd24aa752b9d8c6c008505505ab3e4627a998d35851e9b74f7f6a4c3f1",
    "schema/authoring/v1.4/adr-physical-component.schema.json": "803e856979690a4f7a1eb1983aa5ac2486137eb5f7286ac1d58294bef7115fe8",
    "schema/authoring/v1.4/adr-physical-system.schema.json": "529e0ef9519b6a93850d7a8960e554ad99491105ae537e7b6e2313339ccc86e2",
    "schema/authoring/v1.4/adr-physical.schema.json": "4301e8e10c2ead982015de4dcb79f429466d4e4045f84cf94a4ec5d52ba44b14",
    "schema/authoring/v1.4/types.schema.json": "7dd94ff95772355bfcc7a2ba281d6a6ba9894bb6e12544214e28d173420b2fbc",
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
    "schema/evidence-attribution/v1.1/implementation-attribution-evidence.schema.json": "a51f8b0d8f7b50a6d7747102f88a333eb029356230113223080c50f02c8b0197",
    "schema/evidence-attribution/v1.1/workspace-attribution-federation.schema.json": "838397ce2fde3ed3d643b4b96aa4e6358ab2dabfbe61c2c8033cae8ff0ef9593",
    "schema/evidence-attribution/v1.5/implementation-attribution-evidence.schema.json": "a626acf60834d55fc18defad99ee82d572bc3b87f1cd7c435c4b003c46e01cbc",
    "schema/evidence-attribution/v1.5/semantic-attribution-vocabulary.json": "e4cd5dbaa3d11b432994ea090d6d09c2872d81d0cde761e1d8702a087e4980b8",
    "schema/evidence-attribution/v1.6/implementation-attribution-evidence.schema.json": "abba77be29fcd3c4cabd80cd55b528dd519f7650cb2dcf7e5883a7fe1631fe0f",
    "schema/evidence-attribution/v1.6/semantic-attribution-vocabulary.json": "0a16d6ed2bcc6c1a4b7ca44fd9ff34ce63783dde23aebc55902bdf3805b87bd5",
    "schema/governance/v1.1/decision-ledger.schema.json": "9e5e80da0bf173a4df240e10969f2d420ffa39ac67fc07bd90934db3fbeb2d3d",
    "schema/governance/v1.1/objection-override.schema.json": "4e1ffbbc6ad7a32b7e91221aa15c69f00e2d169ba1df5752f3ad384c5aacd684",
    "schema/governance/v1.1/remediation-ledger.schema.json": "495b2f2292518f5f8e087df7b3ce54a9319f2216bd42e2598b3bb30e3bfb117a",
    "schema/governance/v1.1/requirements-snapshot.schema.json": "10e20552cf1816187ee0109c5b74b5135f0fc41ac1cfbbcecde5772e41937efc",
    "schema/governance/v1.1/steelman-review.schema.json": "8516ed977ae552dc8a750c5fc53ebe9b23220893b75fbc3a280939701ba3f50c",
    "schema/kernel/architecture-index.schema.json": "38c158e51c14cda310d5e84fb765e3ddd1b0926ab2ccd92509a2d50b84cbd285",
    "schema/kernel/entity-registry.schema.json": "9fa2014b8a80d40ce9fa0f2a9101a61f39b503784613b7c87141476b2aae5897",
    "schema/kernel/relationship-registry.schema.json": "60394396a274e38cdfb34392530fbe382fe272427853c654e9e11bbf7730a668",
    "schema/kernel/unresolved-registry.schema.json": "34b20ebe2f2c5f0d746fc0f4a3289409d2d8e2ed15b1cb135da02f17eb8ceb86",
    "schema/migrations/canonical-identity-v13-map.schema.json": "61de7bf2f72c3c86a7a67825a6e24e0502d1052c8c34d8ada00c9481c34316a3",
    "schema/normalized-model/v1.1/normalized-entity-registry.schema.json": "f1b107105d81fef441083cb70a19d56d828af195be8df8e1c10655a162749300",
    "schema/normalized-model/v1.1/relationship-registry.schema.json": "a730b8991cf09967ebbe56b96d315b0f662d51f2e560ab7f61d8b3801ff6b5cf",
    "schema/normalized-model/v1.1/unresolved-registry.schema.json": "23c124becd7ef37a7b4edf49679965d689e8431786f07d69525e95d07df2beae",
    "schema/normalized-model/v2.0/normalized-architecture-model.schema.json": "792e2e82545d0b115466923b00795e8dda08126d7b7aea7c4af571286aa67ab5",
    "schema/normalized-model/v2.0/normalized-entity-registry.schema.json": "38f9002a76517eb16d4e35fd6b14bdf6492e910a7567520da6da52d4b2df2dd6",
    "schema/normalized-model/v2.0/normalized-entity.schema.json": "2fb728c722e8edd18595c04278150d444cab65cc68e9a5187c83026ab4786ac2",
    "schema/normalized-model/v2.0/relationship-record.schema.json": "5fa2fce23ad17792318d40e287299af35b31ae4d501d0a50df257d682ffd8a0f",
    "schema/normalized-model/v2.0/relationship-registry.schema.json": "c563f373dd410e9441736bd12f7837d3a2f8548a9d32073591ca98bc32b0805f",
    "schema/normalized-model/v2.1/normalized-architecture-model.schema.json": "1b35846435e7adc056812e1562368884da0606b1d1f4c5e0cd265c7009a532a0",
    "schema/normalized-model/v2.1/normalized-entity-registry.schema.json": "bff8c7c3e7bd21fbde30f20af6f604f4b6fb8fba1071fd0734ad6456d56f2eaf",
    "schema/normalized-model/v2.1/normalized-entity.schema.json": "0ec2e9692aeca7e21e536147ee541e72891a59cdf563fed16b5215833c1ed661",
    "schema/normalized-model/v2.1/relationship-record.schema.json": "706fa80f1c96173dbc3552a28dd0f71af5fa1791e93d53c11e615cd75ea7a3f1",
    "schema/normalized-model/v2.1/relationship-registry.schema.json": "5372cfb8b5625e468a9a9a9cd9994ad2591829c8ceb44594fceb3cdbf67a1583",
    "schema/normalized-model/v2.1/unresolved-registry.schema.json": "77991b0cdfac9ab12979a66e3945a3faab6923031a06efa68b36a334e4f068b2",
    "schema/normalized-model/v2.2/normalized-architecture-model.schema.json": "fb5f321872256ae6d87b6bb3eea42d9a0d8ca48528f6c0823eb99cae0904f073",
    "schema/normalized-model/v2.2/normalized-entity-registry.schema.json": "7e0c1548abafc4c8828797f57033e2ebcf01090693dc4c1d09283c8381b4f442",
    "schema/normalized-model/v2.2/normalized-entity.schema.json": "7c8fa00d0d16015559ca38388d34c40720b9c435a6313d9d32e99edad2eca2b2",
    "schema/normalized-model/v2.2/relationship-record.schema.json": "19e754bf9045c77bcb2c1a002d3828b92881f8d3e3059dc389a81db6ecc339c0",
    "schema/normalized-model/v2.2/relationship-registry.schema.json": "aaaa058314f3bc67d35f0e6305be1b955e32c4b31b0e8a121a03774e698f1e4d",
    "schema/normalized-model/v2.2/unresolved-registry.schema.json": "035abd6de206ab588b20b431e18a289cbea4e31ea1161f7d6e43de377ee41315",
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
    "schema/v1.0/adr-common.schema.json": "cf9e6460ce53ef2ae8a566dbc383f881bcc0d8f4ac1c5ee8a0d10f0009c5c35d",
    "schema/v1.0/adr-logical.schema.json": "c49d5cebbbd83ed3faa2524ab3af8291606eeaaa9450610efa12e9e392b92c71",
    "schema/v1.0/adr-physical-base.schema.json": "89105a66cec6eddba617192258e44917d0c02956ad8778ac7c6f603e7717d6f5",
    "schema/v1.0/adr-physical-component.schema.json": "f2c922a781aaed64459e661c3bd91f2952288f78ec3b0e089a13f5522390d2c1",
    "schema/v1.0/adr-physical-system.schema.json": "93c2ddb3fcae2a7f3a9f3b7d876ea4cb1b1fb09e659e0de7ad12ca526be7044e",
    "schema/v1.0/adr-physical.schema.json": "44c461b49a48483fb1555c53e62544e838ae0eba17608ec3dbf4ccb6ece10470",
    "schema/v1.0/invariant.schema.json": "5e61818ece9eee3169ab51c24b8ad599a01fd220d336fd4cab4ca64b40a630a1",
    "schema/v1.0/manifest.schema.json": "9335ebfe54640368e251a368a302174a2ab27101b058fbd6de57c60e083d9c6d",
    "schema/v1.0/project-metadata.schema.json": "20ce2b23486864940fa53bb473ca28f674c33668f1cc7689e8b8998081ea2bbb",
    "schema/v1.0/types.schema.json": "b9351f4b010551c53b6ec2cf9d3fb508df082ec8966b81ec0e2b8dc93c3bd1c8",
    "src/adr_kit/schema/authoring/v1_5/adr-common.schema.json": "4800f0c5145cf22c62fd8bcd7037cda8d14ad857c13ee879c7b03bdde70218fb",
    "src/adr_kit/schema/authoring/v1_5/adr-logical.schema.json": "7f1d8a833502db21ef2348cd0a843686c67b54f96d1532cf7c07a2d7fa73340f",
    "src/adr_kit/schema/authoring/v1_5/adr-physical-base.schema.json": "50733ed51dd5c5ecd9fbe150b87ee88fb84c273ff16ee56878be66b7262a6f8c",
    "src/adr_kit/schema/authoring/v1_5/adr-physical-component.schema.json": "fcadb0f6a2bfaf6801c540045cd69cb435be38d68552575ebe2b251f3667951c",
    "src/adr_kit/schema/authoring/v1_5/adr-physical-system.schema.json": "347cb9dfad02a054f9a54d7da8cea1ffc40d5931cd2b4a555614a05a057f91b1",
    "src/adr_kit/schema/authoring/v1_5/types.schema.json": "8a5fb427aad840157599727adab3a948eb88ec9c2a796f8dee41a5951e39c3b3",
    "src/adr_kit/schema/authoring/v1_6/adr-common.schema.json": "6f4d8d0ea8091aa3168e242fe15b973ce301e8c203348eec8cf43ee12932a298",
    "src/adr_kit/schema/authoring/v1_6/adr-logical.schema.json": "3e96f1c3153f541573fe4cf5dd9942db877ed97b9c34a3da6e589b6d60417fbf",
    "src/adr_kit/schema/authoring/v1_6/adr-physical-base.schema.json": "5e146831519ff469fdbee5b2da65bdc0067ea6b6d413b7b98e3fb948dc380fe8",
    "src/adr_kit/schema/authoring/v1_6/adr-physical-component.schema.json": "5fe8d5da0d381774d6d74b14691bb9fa47567d56ee733465eaa06c0d10f7bdb9",
    "src/adr_kit/schema/authoring/v1_6/adr-physical-system.schema.json": "86891426608b68f947fa36016a9cd08da697b0db3a770ee06ecd4be50e63a7a3",
    "src/adr_kit/schema/authoring/v1_6/types.schema.json": "f27df797e88b76956fa4866535133a496e9d65aaedae600e19588deb3a96b16a",
    "src/adr_kit/schema/authoring/v1_7/adr-common.schema.json": "f3c31fa273b6c17eb805a5ddabc2a6d51656e724d4d4ab1193f85a0c12735777",
    "src/adr_kit/schema/authoring/v1_7/adr-logical.schema.json": "5ebcb3ed2b1959cbb9e448fd772b989c9108b6a31c68b327835a1cee95ca7566",
    "src/adr_kit/schema/authoring/v1_7/adr-physical-base.schema.json": "8e34b19d733bb019400a328c753fbb1da27f124ad3d56a1cbcec052883fa3ce5",
    "src/adr_kit/schema/authoring/v1_7/adr-physical-component.schema.json": "021c2e5b443f43c2973c0988a623978d64b8843a9570238db296441fc7260628",
    "src/adr_kit/schema/authoring/v1_7/adr-physical-system.schema.json": "bf9e6f86e84af1b15e20bd3daee53930d01caccbb49c21eae08a68de754e42d6",
    "src/adr_kit/schema/authoring/v1_7/types.schema.json": "3791dbabc32070e4b3cec3ce49934583888e84308076b2fad9603518c276650a",
    "src/adr_kit/schema/migrations/canonical-identity-v13-map.schema.json": "61de7bf2f72c3c86a7a67825a6e24e0502d1052c8c34d8ada00c9481c34316a3",
    "src/adr_kit/schema/v1_0/adr-common.schema.json": "cf9e6460ce53ef2ae8a566dbc383f881bcc0d8f4ac1c5ee8a0d10f0009c5c35d",
    "src/adr_kit/schema/v1_0/adr-logical.schema.json": "c49d5cebbbd83ed3faa2524ab3af8291606eeaaa9450610efa12e9e392b92c71",
    "src/adr_kit/schema/v1_0/adr-physical-base.schema.json": "89105a66cec6eddba617192258e44917d0c02956ad8778ac7c6f603e7717d6f5",
    "src/adr_kit/schema/v1_0/adr-physical-component.schema.json": "f2c922a781aaed64459e661c3bd91f2952288f78ec3b0e089a13f5522390d2c1",
    "src/adr_kit/schema/v1_0/adr-physical-system.schema.json": "93c2ddb3fcae2a7f3a9f3b7d876ea4cb1b1fb09e659e0de7ad12ca526be7044e",
    "src/adr_kit/schema/v1_0/adr-physical.schema.json": "44c461b49a48483fb1555c53e62544e838ae0eba17608ec3dbf4ccb6ece10470",
    "src/adr_kit/schema/v1_0/invariant.schema.json": "5e61818ece9eee3169ab51c24b8ad599a01fd220d336fd4cab4ca64b40a630a1",
    "src/adr_kit/schema/v1_0/manifest.schema.json": "9335ebfe54640368e251a368a302174a2ab27101b058fbd6de57c60e083d9c6d",
    "src/adr_kit/schema/v1_0/project-metadata.schema.json": "20ce2b23486864940fa53bb473ca28f674c33668f1cc7689e8b8998081ea2bbb",
    "src/adr_kit/schema/v1_0/types.schema.json": "b9351f4b010551c53b6ec2cf9d3fb508df082ec8966b81ec0e2b8dc93c3bd1c8",
    "src/adr_kit/schema/v1_1/architecture-index.schema.json": "5a08df6f01a0a37a2fa681acb9b7828cb7720c7287d8367a4d0fadf7fb6e5e80",
    "src/adr_kit/schema/v1_1/decision-ledger.schema.json": "9e5e80da0bf173a4df240e10969f2d420ffa39ac67fc07bd90934db3fbeb2d3d",
    "src/adr_kit/schema/v1_1/entity-registry.schema.json": "98795b46e167affbd35c5415c9f7947d8784c273b918530376d22590d90a047b",
    "src/adr_kit/schema/v1_1/implementation-attribution-evidence.schema.json": "a51f8b0d8f7b50a6d7747102f88a333eb029356230113223080c50f02c8b0197",
    "src/adr_kit/schema/v1_1/normalized-entity-registry.schema.json": "f1b107105d81fef441083cb70a19d56d828af195be8df8e1c10655a162749300",
    "src/adr_kit/schema/v1_1/objection-override.schema.json": "4e1ffbbc6ad7a32b7e91221aa15c69f00e2d169ba1df5752f3ad384c5aacd684",
    "src/adr_kit/schema/v1_1/relationship-registry.schema.json": "a730b8991cf09967ebbe56b96d315b0f662d51f2e560ab7f61d8b3801ff6b5cf",
    "src/adr_kit/schema/v1_1/remediation-ledger.schema.json": "495b2f2292518f5f8e087df7b3ce54a9319f2216bd42e2598b3bb30e3bfb117a",
    "src/adr_kit/schema/v1_1/requirements-snapshot.schema.json": "10e20552cf1816187ee0109c5b74b5135f0fc41ac1cfbbcecde5772e41937efc",
    "src/adr_kit/schema/v1_1/steelman-review.schema.json": "8516ed977ae552dc8a750c5fc53ebe9b23220893b75fbc3a280939701ba3f50c",
    "src/adr_kit/schema/v1_1/unresolved-registry.schema.json": "23c124becd7ef37a7b4edf49679965d689e8431786f07d69525e95d07df2beae",
    "src/adr_kit/schema/v1_1/workspace-attribution-federation.schema.json": "838397ce2fde3ed3d643b4b96aa4e6358ab2dabfbe61c2c8033cae8ff0ef9593",
    "src/adr_kit/schema/v1_2/adr-common.schema.json": "a91a351c4e7c8ddf85c3395d366f1de9782fb1fdd89466dade5522567cd3d50c",
    "src/adr_kit/schema/v1_2/adr-logical.schema.json": "f8b62b44e19e03be6b8c17c6b9cbc8ae26cc0e59d5c50f1149abb8fcccd13ba1",
    "src/adr_kit/schema/v1_2/adr-physical-base.schema.json": "7be1399209bc7fac890786ff8807ed071d0e0aa90767c0129776a025b67a5d36",
    "src/adr_kit/schema/v1_2/adr-physical-component.schema.json": "93979efe12c8ba4e1d79b197ee1dbf1985bfc3523835c30592027bf2307c985d",
    "src/adr_kit/schema/v1_2/adr-physical-system.schema.json": "4ea0ca069bb0e8780c32947d3b8bbc32d91b3aff7b1b1b612298131bf61afc06",
    "src/adr_kit/schema/v1_2/adr-physical.schema.json": "6452e57d0d24381bf051e674e12fe96ca1c973aad72f531236cb67339f970533",
    "src/adr_kit/schema/v1_2/invariant.schema.json": "210cc15723c9e5437673991e3e4a0154fb3ca529adf032088924bdd7890b7deb",
    "src/adr_kit/schema/v1_2/types.schema.json": "6c433753a43c8dd279f5aec12e81b8876c9360a04db8d817bca10246f2a00f8a",
    "src/adr_kit/schema/v1_3/adr-common.schema.json": "a585ba26a5d1cb326d09f7e8da59d3a05a4bccac1aabe02b9a8d6b82bf5926e9",
    "src/adr_kit/schema/v1_3/adr-logical.schema.json": "fccec445b37f43458ccfc7d524d26fb3f609e8765089383c2beea9df802e22f0",
    "src/adr_kit/schema/v1_3/adr-physical-base.schema.json": "0360b15e07bb91639e3b382578e3116cacbc97f30ad7e0f7ff7b91803257083f",
    "src/adr_kit/schema/v1_3/adr-physical-component.schema.json": "e96fef221b66484b17993361618b6b219d6ed6a567f335948f068ae1f3ad31da",
    "src/adr_kit/schema/v1_3/adr-physical-system.schema.json": "86f0ceaa9c84ab64be908ce7f87b302db04ee12f842e69bc0126dde0f1ee5b09",
    "src/adr_kit/schema/v1_3/adr-physical.schema.json": "094d65d02cdd08cda70cb9e000326a9204bce73c7cbaae135225ec6568a669f4",
    "src/adr_kit/schema/v1_3/types.schema.json": "612d73a201177db340bbb8beab7abd83b1b940f9d262abe85bb4ea5457369816",
    "src/adr_kit/schema/v1_4/adr-common.schema.json": "8d80bf29c59b4e04e6dbe42b0ff2339ee16ce43c5228af71a409ece597a00c98",
    "src/adr_kit/schema/v1_4/adr-logical.schema.json": "c413604d70e8750f5f1d6f6b78dcc5e207a2756a603940dfc4a7eb719b757c50",
    "src/adr_kit/schema/v1_4/adr-physical-base.schema.json": "1ec099dd24aa752b9d8c6c008505505ab3e4627a998d35851e9b74f7f6a4c3f1",
    "src/adr_kit/schema/v1_4/adr-physical-component.schema.json": "803e856979690a4f7a1eb1983aa5ac2486137eb5f7286ac1d58294bef7115fe8",
    "src/adr_kit/schema/v1_4/adr-physical-system.schema.json": "529e0ef9519b6a93850d7a8960e554ad99491105ae537e7b6e2313339ccc86e2",
    "src/adr_kit/schema/v1_4/adr-physical.schema.json": "4301e8e10c2ead982015de4dcb79f429466d4e4045f84cf94a4ec5d52ba44b14",
    "src/adr_kit/schema/v1_4/types.schema.json": "7dd94ff95772355bfcc7a2ba281d6a6ba9894bb6e12544214e28d173420b2fbc",
    "src/adr_kit/schema/v1_5/implementation-attribution-evidence.schema.json": "a626acf60834d55fc18defad99ee82d572bc3b87f1cd7c435c4b003c46e01cbc",
    "src/adr_kit/schema/v1_5/semantic-attribution-vocabulary.json": "e4cd5dbaa3d11b432994ea090d6d09c2872d81d0cde761e1d8702a087e4980b8",
    "src/adr_kit/schema/v1_6/implementation-attribution-evidence.schema.json": "abba77be29fcd3c4cabd80cd55b528dd519f7650cb2dcf7e5883a7fe1631fe0f",
    "src/adr_kit/schema/v1_6/semantic-attribution-vocabulary.json": "0a16d6ed2bcc6c1a4b7ca44fd9ff34ce63783dde23aebc55902bdf3805b87bd5",
    "src/adr_kit/schema/v2_0/normalized-architecture-model.schema.json": "792e2e82545d0b115466923b00795e8dda08126d7b7aea7c4af571286aa67ab5",
    "src/adr_kit/schema/v2_0/normalized-entity-registry.schema.json": "38f9002a76517eb16d4e35fd6b14bdf6492e910a7567520da6da52d4b2df2dd6",
    "src/adr_kit/schema/v2_0/normalized-entity.schema.json": "2fb728c722e8edd18595c04278150d444cab65cc68e9a5187c83026ab4786ac2",
    "src/adr_kit/schema/v2_0/relationship-record.schema.json": "5fa2fce23ad17792318d40e287299af35b31ae4d501d0a50df257d682ffd8a0f",
    "src/adr_kit/schema/v2_0/relationship-registry.schema.json": "c563f373dd410e9441736bd12f7837d3a2f8548a9d32073591ca98bc32b0805f",
    "src/adr_kit/schema/v2_1/normalized-architecture-model.schema.json": "1b35846435e7adc056812e1562368884da0606b1d1f4c5e0cd265c7009a532a0",
    "src/adr_kit/schema/v2_1/normalized-entity-registry.schema.json": "bff8c7c3e7bd21fbde30f20af6f604f4b6fb8fba1071fd0734ad6456d56f2eaf",
    "src/adr_kit/schema/v2_1/normalized-entity.schema.json": "0ec2e9692aeca7e21e536147ee541e72891a59cdf563fed16b5215833c1ed661",
    "src/adr_kit/schema/v2_1/relationship-record.schema.json": "706fa80f1c96173dbc3552a28dd0f71af5fa1791e93d53c11e615cd75ea7a3f1",
    "src/adr_kit/schema/v2_1/relationship-registry.schema.json": "5372cfb8b5625e468a9a9a9cd9994ad2591829c8ceb44594fceb3cdbf67a1583",
    "src/adr_kit/schema/v2_1/unresolved-registry.schema.json": "77991b0cdfac9ab12979a66e3945a3faab6923031a06efa68b36a334e4f068b2",
    "src/adr_kit/schema/v2_2/normalized-architecture-model.schema.json": "fb5f321872256ae6d87b6bb3eea42d9a0d8ca48528f6c0823eb99cae0904f073",
    "src/adr_kit/schema/v2_2/normalized-entity-registry.schema.json": "7e0c1548abafc4c8828797f57033e2ebcf01090693dc4c1d09283c8381b4f442",
    "src/adr_kit/schema/v2_2/normalized-entity.schema.json": "7c8fa00d0d16015559ca38388d34c40720b9c435a6313d9d32e99edad2eca2b2",
    "src/adr_kit/schema/v2_2/relationship-record.schema.json": "19e754bf9045c77bcb2c1a002d3828b92881f8d3e3059dc389a81db6ecc339c0",
    "src/adr_kit/schema/v2_2/relationship-registry.schema.json": "aaaa058314f3bc67d35f0e6305be1b955e32c4b31b0e8a121a03774e698f1e4d",
    "src/adr_kit/schema/v2_2/unresolved-registry.schema.json": "035abd6de206ab588b20b431e18a289cbea4e31ea1161f7d6e43de377ee41315",
    "src/adr_kit/schema/v2_3/normalized-architecture-model.schema.json": "0a85eaf60a128a0d09d16cc83c98c7d1c236783bed86a19cae87a20a8935ad3b",
    "src/adr_kit/schema/v2_3/normalized-entity-registry.schema.json": "62bc9f42a0fc67edf6bec9dbdfb0499c0fcfe7f6f031a884855c544cc6909cef",
    "src/adr_kit/schema/v2_3/normalized-entity.schema.json": "ba7bdd180a2f2ca838f885415c790a67cfd720c34779f4ef07e3eeaf062ee819",
    "src/adr_kit/schema/v2_3/relationship-record.schema.json": "af36fc51822e3998e8ac2c1f17be8245470feea874862f177dd536cfd9fdf658",
    "src/adr_kit/schema/v2_3/relationship-registry.schema.json": "3702cd68fa5a5acb74da804c7acde55840fd338c792b7e8f261721490a4fc51d",
    "src/adr_kit/schema/v2_3/unresolved-registry.schema.json": "13461e3ec17069312e39063e4bf921ddebb0635d17f86640622143a1de5057b4",
    "src/adr_kit/schema/v2_4/normalized-architecture-model.schema.json": "d7fe9ea9cc6a7d67d52b4190cc47f331a738bd85cddace147c6d7504f7a19df0",
    "src/adr_kit/schema/v2_4/normalized-entity-registry.schema.json": "8c82185dba5cd2692830252cef497b54a94c61c089e00f1edb12cd355da7bc1f",
    "src/adr_kit/schema/v2_4/normalized-entity.schema.json": "4ee0ee77dbc7746f60c33f85c2ccc10ae4fbc1f419e5955b0b449e179581497d",
    "src/adr_kit/schema/v2_4/relationship-record.schema.json": "517edc9218c18aae0a51418ede7af086c692e13bc16365152e9ab038863ab0c4",
    "src/adr_kit/schema/v2_4/relationship-registry.schema.json": "a27b5e95ac1abebe01f27f14037df0127b06c36e0dfed37268f1d82bc8ee9390",
    "src/adr_kit/schema/v2_4/unresolved-registry.schema.json": "ed54fa1446343e5b5100f2e6fb45742c6768781cef97893a41b7245ebc8d757a",
    "src/adr_kit/schema/v2_5/normalized-architecture-model.schema.json": "6e61d23e8a1c0722727b8fe50ae915299fd310dab3cd1ae183a0435cd234d35b",
    "src/adr_kit/schema/v2_5/normalized-entity-registry.schema.json": "972a7264b0830508c3627ee77aec12b13a174a28e5292fa9981aca5bc906ade7",
    "src/adr_kit/schema/v2_5/normalized-entity.schema.json": "0a44d2119b082ec622461e4f7d71d54143be8d79e0f1985a677feaa0f7bbc162",
    "src/adr_kit/schema/v2_5/relationship-record.schema.json": "f38a36b1d0ad419c47b40b3924fa743a47e44403fd93e2e0ee4059c9e7d3c1e9",
    "src/adr_kit/schema/v2_5/relationship-registry.schema.json": "c9a5b6adcc0e109fa22ad674c94ec04912016b00dad02ba891902cbc5d152149",
    "src/adr_kit/schema/v2_5/unresolved-registry.schema.json": "0e46627fc741581e5fc218ce235b68d9981085b88cea0ac6c6893eb0e3d31919",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.1.json": "f4682920485823f85bd77c78fcea0e34fb1d167ea854198b6228a9a2733c06e3",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.2.json": "b3f00596c164109098b9020964c1a9bfafc52b345e6024941cb0bf50d3d3d6c5",
    "src/adr_kit/semantic_contract/v1_0/architecture-interpretation.json": "763c23e826e17898e40d0964a7848aa7bab930bf1140cc0e1c62300b952d5c6f",
    "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.0.json": "81df32e4044fc92937b1bb812ee1d9259f290b938be29e868d0597eee30ec1f1",
    "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.1.json": "02f938ea53e76b83a83d9319029e09a4055d9c75da4b6955f0a80dd72fce836a",
    "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.2.json": "5cfd8b8f9a50351316f9f92e498b96e9d09569c0da6d0b9dc9fa308fd2a6dc80",
    "src/adr_kit/semantic_contract/v1_0/catalog/semantic-contract-catalog-1.0.json": "44805f34c9785539d5edb8ab3b70d1add02f6365d75c4a9e2df156a03d7a9c34",
    "src/adr_kit/semantic_contract/v1_0/current/semantic-contract-current-1.0.json": "a56db66274fecf7442d314afdf1d183b0284b3ef56ae45381258ea8f1f9d7100",
    "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.1.json": "f4682920485823f85bd77c78fcea0e34fb1d167ea854198b6228a9a2733c06e3",
    "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.2.json": "b3f00596c164109098b9020964c1a9bfafc52b345e6024941cb0bf50d3d3d6c5",
    "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.0.json": "81df32e4044fc92937b1bb812ee1d9259f290b938be29e868d0597eee30ec1f1",
    "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.1.json": "02f938ea53e76b83a83d9319029e09a4055d9c75da4b6955f0a80dd72fce836a",
    "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.2.json": "5cfd8b8f9a50351316f9f92e498b96e9d09569c0da6d0b9dc9fa308fd2a6dc80",
    "src/adr_kit/semantic_contract/v1_0/definitions/normalized-model-2.4.json": "22d4f8523c691599303af64dbe259f59e97ae68d17ae09da5ac6ef677b91fde0",
    "src/adr_kit/semantic_contract/v1_0/definitions/normalized-model-2.5.json": "e465444fec27cb5a43efbdb96f502025d31755be5ed5ed8c16329d699d859a85",
    "src/adr_kit/semantic_contract/v1_0/definitions/normative-semantics-1.0.json": "3682a5031b3232e1a7ff86af8101632336f2be67bb0795f1ca78076b61543430",
    "src/adr_kit/semantic_contract/v1_0/normalized-model-2.4.json": "22d4f8523c691599303af64dbe259f59e97ae68d17ae09da5ac6ef677b91fde0",
    "src/adr_kit/semantic_contract/v1_0/normalized-model-2.5.json": "e465444fec27cb5a43efbdb96f502025d31755be5ed5ed8c16329d699d859a85",
    "src/adr_kit/semantic_contract/v1_0/normalized-model.json": "fea7398f854155933a414d327c4e08d97cbd469e8503f13558c12e426971bd50",
    "src/adr_kit/semantic_contract/v1_0/normative-semantics-1.0.json": "3682a5031b3232e1a7ff86af8101632336f2be67bb0795f1ca78076b61543430",
    "src/adr_kit/semantic_contract/v1_0/normative-semantics.json": "3682a5031b3232e1a7ff86af8101632336f2be67bb0795f1ca78076b61543430",
    "src/adr_kit/semantic_contract/v1_0/policy/semantic-contract-policy-1.0.json": "52d3aac6a8ca76958712e7a574d8f6ad654cf0edfe1dafd52a142a1c5bcc050a",
    "src/adr_kit/semantic_contract/v1_0/profiles/architecture-materialization-1.0.json": "2d1c324a3846ced1909e341d5e3b6ef59295d9f8df30b95888672f0388cd1597",
    "src/adr_kit/semantic_contract/v1_0/profiles/architecture-materialization-1.1.json": "ff33d9b8556a1c7b1b12f4b932d86ba6a9ebe0f3d8e34f2f2341f77b5b50b688",
    "src/adr_kit/semantic_contract/v1_0/qualifications/architecture-materialization-1.0.json": "e1d912bc509873bd6377f0de90bef805120978f03fd96aae680def444563c8c3",
    "src/adr_kit/semantic_contract/v1_0/qualifications/architecture-materialization-1.1.json": "d22c72a4109a5b7276469254ad781118830b37803c029ef992d24ba133a20a91",
    "src/adr_kit/semantic_contract/v1_0/resource-manifest-entry.schema.json": "bc6df72ffae3d096b93809e9de06a9e019488aa63610dd2bbad8803c59ecd582",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-conformance.json": "92b43e5998530d35a1153dd7bfb29ea151f8a7a8cb41eeb0633bd099eaa9a2bc",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-legacy-compatibility.json": "93220b51293b8cd483e0b80611b47c46f4f1fa040d3b951da98fc2cd748c9de1",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-rules.json": "6e41a7379f5564406c059a8eb4e9bfbf420fabc2c606273733baa9419fa2d5eb",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-source-decoding-1.7.json": "5f3ff45ba5a7f3e71ce27c9bd83c6d63b7fec0f01d67dc51710d7cdddf3a16d1",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.1-source-mapping-1.7-to-2.4.json": "e195805840a3c99f58c0d16c2526d44c1d818db4d3ba347c9180502dec1e4cda",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-conformance.json": "d5518ca8d18264fe21fb69cee39590d8e5bfa22151dc31ba2016235b8ff3e2ce",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-conformance.schema.json": "591b79cb230284a7ef9f48591e8563d8e7cba332a53af3cd1b39d9c8f13aa0fa",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-contract.json": "b3f00596c164109098b9020964c1a9bfafc52b345e6024941cb0bf50d3d3d6c5",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-detached-context.json": "0c713f4b90ccb60f397f6506e702da110cc5567cf0b05fd9f6fd8759a7ed7e8f",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-field-dispositions-1.7-to-2.4.json": "d83bbccd0e2baca895063404fe632f058174dd8adeab2b4fc0a1d9eb51e1ddf4",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-field-dispositions.schema.json": "9bb2e9195c12fee0120df40b60ed6b926601f88824a621b4b7e5885b92f931c1",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-legacy-compatibility.json": "39a99cb149ebdbd553d3d21c190163bc2ade06b6b482da2090a96c4a902fe54c",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-rules.json": "d3c6dd118e0cffa63c5344cc62361f057b4ca0f58503effc12a5481770e9c5f5",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-source-decoding-1.7.json": "df71b391ea494a37075ff910386a2017580db9388c376cab7479903552fa09a1",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-1.2-source-mapping-1.7-to-2.4.json": "67ff7cde821eb22fc148861a1d42fcd83a7260e92ebc4abdfe72f040521020ef",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-conformance.json": "718a7fc17405d9ce3c946f01348fd40ab6c3061d346c399928b03e7ea0e3770b",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-rules.json": "ae6fe83091ac9da60e460163755fa67aae37303e7bdbebdd4889e38184dffe6b",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-source-decoding-1.5.json": "026cc5e40d011a9928c3fba20f84851fd5d64e951627ad851d69033c98e39e61",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-source-decoding-1.6.json": "004bace3f3f05c7a97556ed6fab34a094e749de44e8c728c9686d36d709ac4fa",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-source-mapping-1.5-to-2.3.json": "e140efc81dded6488f0a27f59e87dac8b24dc21bc03060403945706ed10a6590",
    "src/adr_kit/semantic_contract/v1_0/resources/architecture-interpretation-source-mapping-1.6-to-2.3.json": "466c4554c9ad0545ee0e9256e955e24844d16b37bbbc11b26154b2705f7fe85f",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-common.schema.json": "4800f0c5145cf22c62fd8bcd7037cda8d14ad857c13ee879c7b03bdde70218fb",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-logical.schema.json": "7f1d8a833502db21ef2348cd0a843686c67b54f96d1532cf7c07a2d7fa73340f",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-physical-base.schema.json": "50733ed51dd5c5ecd9fbe150b87ee88fb84c273ff16ee56878be66b7262a6f8c",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-physical-component.schema.json": "fcadb0f6a2bfaf6801c540045cd69cb435be38d68552575ebe2b251f3667951c",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-adr-physical-system.schema.json": "347cb9dfad02a054f9a54d7da8cea1ffc40d5931cd2b4a555614a05a057f91b1",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.5-schema-types.schema.json": "8a5fb427aad840157599727adab3a948eb88ec9c2a796f8dee41a5951e39c3b3",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-common.schema.json": "6f4d8d0ea8091aa3168e242fe15b973ce301e8c203348eec8cf43ee12932a298",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-logical.schema.json": "3e96f1c3153f541573fe4cf5dd9942db877ed97b9c34a3da6e589b6d60417fbf",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-physical-base.schema.json": "5e146831519ff469fdbee5b2da65bdc0067ea6b6d413b7b98e3fb948dc380fe8",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-physical-component.schema.json": "5fe8d5da0d381774d6d74b14691bb9fa47567d56ee733465eaa06c0d10f7bdb9",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-adr-physical-system.schema.json": "86891426608b68f947fa36016a9cd08da697b0db3a770ee06ecd4be50e63a7a3",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.6-schema-types.schema.json": "f27df797e88b76956fa4866535133a496e9d65aaedae600e19588deb3a96b16a",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-common.schema.json": "f3c31fa273b6c17eb805a5ddabc2a6d51656e724d4d4ab1193f85a0c12735777",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-logical.schema.json": "5ebcb3ed2b1959cbb9e448fd772b989c9108b6a31c68b327835a1cee95ca7566",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-physical-base.schema.json": "8e34b19d733bb019400a328c753fbb1da27f124ad3d56a1cbcec052883fa3ce5",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-physical-component.schema.json": "021c2e5b443f43c2973c0988a623978d64b8843a9570238db296441fc7260628",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-adr-physical-system.schema.json": "bf9e6f86e84af1b15e20bd3daee53930d01caccbb49c21eae08a68de754e42d6",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-1.7-schema-types.schema.json": "3791dbabc32070e4b3cec3ce49934583888e84308076b2fad9603518c276650a",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.0-conformance.json": "2b88de11e8d4cd8bea7e2c27a2edc781a20663a335cc38c6e2b4f29dd182df67",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.0-contract.json": "81df32e4044fc92937b1bb812ee1d9259f290b938be29e868d0597eee30ec1f1",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.0-rules.json": "e70191c3386224d68279e3c355baf10049463f83f3d1981936eb16fd76ecf7ad",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-compatibility.json": "b1f917e741c7fc081d471c97729146016e3563f4bf93abd04e8e0f3eb9b73434",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-conformance.json": "725e55a808d4f1e5eb0819928d67d58fa02e586237587a53b44a6f8af798c86e",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-conformance.schema.json": "16a8b7f94341fb72ee6c643c68971f2ee4fc538471b0d655e0fd88046af617e4",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-contract.json": "02f938ea53e76b83a83d9319029e09a4055d9c75da4b6955f0a80dd72fce836a",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-ledger.schema.json": "4d0caa154c61ceca80b0da504ae368f130461e4fe445a07c46d7e156388f50ec",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-rules.json": "6ea14c2eed67804e763dac7a6ab9232648d416e582826a70d2a7c2e0b61757ac",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.1-schema.json": "c37c5206dce55e14e1f3d56a8c90a3ce4b6d4b720870b27ac31986c447d45208",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-compatibility.json": "3c2ab4b284ad78a154782b04653977994c0e9a4bf58ed5fd8ea7f70f33647402",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-composition-bindings.json": "0b8c8d1d37664e4e36cc0fc703c5cea13db4cd4294b0bfb48ed2743f4aa9adb8",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-composition-bindings.schema.json": "e15c843f4b27c0df1d69668f1335bd79f0ba54548beb79baa25bc273cc91456e",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-conformance.json": "8d9268252dc7dcfbe3971dc804bd265990aa64249bc09c87796f9f2f69e27c8a",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-conformance.schema.json": "7550726ca21de1d9155c6eaf3f64ba205115433ac55524c61cfb4ced3885f17a",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-rules.json": "e79f487155f96627563ae1156b0ffa6d9b6b5fe8ce1f098114300da2c80ce292",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-construction-1.2-schema.json": "79e705ecf53f9c8834a5ea1708d08be72f12f670fc43eace1c7b9ef14606175c",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-domain-1.1-contract.json": "082d6c63211f2611e85d38fe7b674180c8c8276859d56b010830c6c381d01c6f",
    "src/adr_kit/semantic_contract/v1_0/resources/authoring-domain-1.1-schema.json": "766d8bd3c29de24d9163dd216b5e6a5dc4e7ab052b70828491c6bf03114ec2f9",
    "src/adr_kit/semantic_contract/v1_0/resources/custom-entity-1.0-conformance.json": "7df4c32e355fd4d77145bd07a7d2cc04ca0022a324b42b24191e930b6cb1f94b",
    "src/adr_kit/semantic_contract/v1_0/resources/custom-entity-1.0-contract.json": "9669f12be495c944d0f53fabd1004fbf49387dafe63618dcc64fc5bf0c6a4060",
    "src/adr_kit/semantic_contract/v1_0/resources/custom-entity-1.0-schema.json": "6ee9cb18c64975b1c72507b34cb76dde9f7e58e9310ceb285ab697d2683d7caf",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-conformance.json": "83b430f0fdd5cc2eb128dc197e97641f9e7a2f6afc7b0177f4b7b9bb5fe5b001",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-normalized-architecture-model.schema.json": "0a85eaf60a128a0d09d16cc83c98c7d1c236783bed86a19cae87a20a8935ad3b",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-normalized-entity-registry.schema.json": "62bc9f42a0fc67edf6bec9dbdfb0499c0fcfe7f6f031a884855c544cc6909cef",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-normalized-entity.schema.json": "ba7bdd180a2f2ca838f885415c790a67cfd720c34779f4ef07e3eeaf062ee819",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-relationship-record.schema.json": "af36fc51822e3998e8ac2c1f17be8245470feea874862f177dd536cfd9fdf658",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-relationship-registry.schema.json": "3702cd68fa5a5acb74da804c7acde55840fd338c792b7e8f261721490a4fc51d",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.3-schema-unresolved-registry.schema.json": "13461e3ec17069312e39063e4bf921ddebb0635d17f86640622143a1de5057b4",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-conformance.json": "7fe75c9ea6899aaf075a10b684a16a7f973ab3cf6df20d5459d1e31e31eccbf1",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-architecture-model.schema.json": "d7fe9ea9cc6a7d67d52b4190cc47f331a738bd85cddace147c6d7504f7a19df0",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-entity-registry.schema.json": "8c82185dba5cd2692830252cef497b54a94c61c089e00f1edb12cd355da7bc1f",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-normalized-entity.schema.json": "4ee0ee77dbc7746f60c33f85c2ccc10ae4fbc1f419e5955b0b449e179581497d",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-relationship-record.schema.json": "517edc9218c18aae0a51418ede7af086c692e13bc16365152e9ab038863ab0c4",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-relationship-registry.schema.json": "a27b5e95ac1abebe01f27f14037df0127b06c36e0dfed37268f1d82bc8ee9390",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.4-schema-unresolved-registry.schema.json": "ed54fa1446343e5b5100f2e6fb45742c6768781cef97893a41b7245ebc8d757a",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-conformance.json": "49c9ee5614e601aee56f65cca17549b0046b43e0fa837962c2f9207e00e5d82c",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-normalized-architecture-model.schema.json": "6e61d23e8a1c0722727b8fe50ae915299fd310dab3cd1ae183a0435cd234d35b",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-normalized-entity-registry.schema.json": "972a7264b0830508c3627ee77aec12b13a174a28e5292fa9981aca5bc906ade7",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-normalized-entity.schema.json": "0a44d2119b082ec622461e4f7d71d54143be8d79e0f1985a677feaa0f7bbc162",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-relationship-record.schema.json": "f38a36b1d0ad419c47b40b3924fa743a47e44403fd93e2e0ee4059c9e7d3c1e9",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-relationship-registry.schema.json": "c9a5b6adcc0e109fa22ad674c94ec04912016b00dad02ba891902cbc5d152149",
    "src/adr_kit/semantic_contract/v1_0/resources/normalized-model-2.5-schema-unresolved-registry.schema.json": "0e46627fc741581e5fc218ce235b68d9981085b88cea0ac6c6893eb0e3d31919",
    "src/adr_kit/semantic_contract/v1_0/resources/normative-semantics-conformance.json": "189049af5fa3612fda182ce9995fe8e6bde7fa921ed13a1072143e7fb123a170",
    "src/adr_kit/semantic_contract/v1_0/resources/normative-semantics-definition.json": "17a7909dd5de9da9cc7001aace0100da86942953e9c3010b212df410f6bebec5",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-assembly-request.schema.json": "b10e7382456dc00f33f9dd50576e5bda69b46b971f492df33eac74c7edfdf894",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-assembly-result.schema.json": "a336121eec1abf83a1fbe1d99de32e89e5b19c3bb005c5db284429b43b4582a0",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-catalog.schema.json": "21269bd3e327e893f7841522e953c0a4330d73b68cc171416dd33d4066c618c5",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-corpus-validation-request.schema.json": "e46b48cedf51b0767167b27093ee96ebb0615e5aae6bdf0179302a9b705920b0",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-corpus-validation-result.schema.json": "5a14c5fe769623cf47660e4651f4af6bad411dd7ebb78813932cd59abebaad5c",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-current-resolution-request.schema.json": "9577f1fd2f88c7a0ec98b076cdda202954ab1056b371dd2757bbb2400c9f23ce",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-current-resolution-result.schema.json": "f8819fca0b75ad86ef8a5ef668c87c605f6d35b1e0f2f303aef3bfa1d7a9abc8",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-current-selection.schema.json": "55802431060dbbf1c667927c1337971db4bf3df6aee2509321deeb477c889573",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-policy.schema.json": "e7e794780c58eb81d3bdd26fcac4a6ab4468a621985f84d4cda2a9da78116b96",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-profile.schema.json": "14f7784620c559ed1dbcb8cae2f5557a768413e94b16b773452af8fb2fcb67ee",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-qualification.schema.json": "71c70568311208c2549469cd8e44fec02f1a39a1ba364b0214c62ed25ded63f5",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-set.schema.json": "a3bcdf9978b840b7bb3235c0861c1ab8ed87fab0296f5c5ff1221d7d6539ff42",
    "src/adr_kit/semantic_contract/v1_0/semantic-contract-version.schema.json": "92056ccb9f7ca59ddb2d9d527e3ac8a09db8ad89c7607ce0baef34e1efde5a58",
    "src/adr_kit/semantic_contract/v1_0/sets/scs-v1-sha256-2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020.json": "500e6f8dbafefaa94272d2632bad34856d63a8c47b5b5f4331560bc0a54329f6",
    "src/adr_kit/semantic_contract/v1_0/sets/scs-v1-sha256-d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6.json": "35c419c4fdcfdf47b6d001672758a6a0b485f041425c9405f39548f05a1f9c4d",
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def rows() -> list[dict[str, Any]]:
    return read(CANONICAL / "resources/lifecycle-ownership.json")["rows"]


def carrier(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "declaring_adr_id": UUID,
        "declaring_adr_semantic_type": row["declaring_adr_semantic_type"],
        "status_semantic_field_key": row["status_semantic_field_key"],
        "status_source_authority": row["status_source_authority"],
        "ownership_rule": {
            "family": "architecture-interpretation",
            "version": "1.3",
            "semantic_contract_fingerprint": EXPECTED_SCF,
            "canonical_resource_key": publication.AI + "lifecycle-ownership",
            "content_digest": next(
                e.content_digest
                for e in get_semantic_contract(
                    "architecture-interpretation", "1.3"
                ).resource_manifest
                if e.canonical_resource_key == publication.AI + "lifecycle-ownership"
            ),
            "rule_id": row["rule_id"],
        },
        "value_destination": "/lifecycle_stage",
    }


@pytest.fixture
def candidate(tmp_path: Path) -> Path:
    for relative in (
        "schema/authoring/v1.7",
        "schema/normalized-model/v2.5",
        "contracts/architecture-interpretation/v1.2",
        "contracts/architecture-interpretation/v1.3",
    ):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    relative = "contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json"
    (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / relative, tmp_path / relative)
    return tmp_path


def test_exact_scf_complete_closure_and_version_schema() -> None:
    contract = get_semantic_contract("architecture-interpretation", "1.3")
    assert contract.semantic_contract_fingerprint == EXPECTED_SCF
    assert (
        calculate_semantic_contract_fingerprint(contract).semantic_contract_fingerprint
        == EXPECTED_SCF
    )
    assert verify_semantic_contract(contract).success
    assert not list(
        Draft202012Validator(read(CANONICAL / "schema.json")).iter_errors(contract.to_wire())
    )
    assert contract.frozen_normative_conformance_resources == (publication.AI + "conformance",)
    assert len(contract.resource_manifest) == 52
    bundle = [
        {
            "canonicalResourceKey": e.canonical_resource_key,
            "content": load_semantic_resource(e.canonical_resource_key),
        }
        for e in contract.resource_manifest
    ]
    assert validate_semantic_resource_closure(contract, bundle).closure_valid
    assert validate_semantic_resource_closure(contract, list(reversed(bundle))).closure_valid
    keys = {e.canonical_resource_key for e in contract.resource_manifest}
    assert "architecture-interpretation/1.2/source-decoding-1.7" in keys
    assert "architecture-interpretation/1.2/legacy-compatibility" in keys
    assert {key for key in keys if key.startswith(publication.AI)} == {
        publication.AI + name for name in publication.RESOURCE_NAMES
    }


@pytest.mark.parametrize("fault", ["missing", "altered", "duplicate", "extra", "scf", "dependency"])
def test_integrity_faults_fail_closed(fault: str) -> None:
    contract = get_semantic_contract("architecture-interpretation", "1.3")
    bundle = [
        {
            "canonicalResourceKey": e.canonical_resource_key,
            "content": load_semantic_resource(e.canonical_resource_key),
        }
        for e in contract.resource_manifest
    ]
    if fault == "missing":
        bundle.pop()
    elif fault == "altered":
        next(e for e in bundle if e["canonicalResourceKey"] == publication.AI + "rules")["content"][
            "identity"
        ] = {}
    elif fault == "duplicate":
        bundle.append(bundle[-1])
    elif fault == "extra":
        bundle.append({"canonicalResourceKey": publication.AI + "extra", "content": {}})
    else:
        wire = contract.to_wire()
        if fault == "dependency":
            next(e for e in wire["resourceManifest"] if e["dependencies"])["dependencies"].pop()
            wire["semanticContractFingerprint"] = calculate_semantic_contract_fingerprint(
                wire
            ).semantic_contract_fingerprint
        else:
            wire["semanticContractFingerprint"] = "scf:v1:sha256:" + "0" * 64
        contract = SemanticContractVersion.from_wire(wire)
    assert not validate_semantic_resource_closure(contract, bundle).success


def test_all_catalogs_and_twenty_enum_domains_are_qualified() -> None:
    result = publication.qualify_publication(ROOT)
    assert result["ownership_selectors"] == 17
    assert result["built_in_types"] == 13
    assert result["runtime_interpretation"] is False
    assert len(result["enum_domain_proofs"]) == 20
    for proof in result["enum_domain_proofs"]:
        assert proof["source_domain"] == ["accepted", "deprecated", "proposed", "superseded"]
        assert proof["unchanged_values_accepted"] is True
        assert proof["destination_selector"] == "/oneOf/0/properties/lifecycle_stage"


def test_exact_selector_coverage_and_nested_interface_owner() -> None:
    expected = publication.derive_ownership_rows(ROOT)
    assert expected == rows()
    assert Counter(row["declaring_adr_semantic_type"] for row in expected) == {
        "adr/logical": 7,
        "adr/physical-component": 5,
        "adr/physical-system": 5,
    }
    interface = next(row for row in expected if row["child_semantic_type"] == "entity/interface")
    assert interface["parent_semantic_type"] == "entity/component"
    assert interface["declaring_adr_semantic_type"] == "adr/physical-component"
    assert interface["source_instance_pattern"] == "/component_specifications/*/interfaces/*"
    assert len(interface["ownership_schema_path"]) == 2
    system = next(row for row in expected if row["child_semantic_type"] == "entity/system")
    assert (
        system["shared_system_descriptor"]
        == "reuse_existing_semantic_unit_if_same_canonical_identity"
    )
    excluded = {"entity/normative_proposition", "entity/extension"}
    assert not excluded & {row["child_semantic_type"] for row in expected}
    assert all(row["declaring_adr_identity_selector"] == "/id" for row in expected)


def test_successor_semantic_extensions_and_context_select_successor_authority() -> None:
    rules = read(CANONICAL / "resources/rules.json")
    assert rules["semantic_extensions"]["carrier"]["contract_family"] == "normalized-model"
    assert rules["semantic_extensions"]["carrier"]["contract_version"] == "2.5"
    assert (
        rules["semantic_extensions"]["meaning_authority"]["contract_family"]
        == "architecture-interpretation"
    )
    assert rules["semantic_extensions"]["meaning_authority"]["contract_version"] == "1.3"
    context = read(CANONICAL / "resources/detached-context.json")
    assert context["derivation"]["contract_identity"] == (
        "exact AI 1.3 and NM 2.5 identities participate in context qualification but not locator derivation"
    )


@pytest.mark.parametrize("index", range(17))
def test_closed_carrier_schema_accepts_each_qualified_rule_shape(index: int) -> None:
    schema = read(CANONICAL / "resources/lifecycle-provenance.schema.json")
    assert Draft202012Validator(schema).is_valid(carrier(rows()[index]))


@pytest.mark.parametrize(
    "fault",
    [
        "missing_owner",
        "bad_uuid",
        "duplicate_value",
        "unknown_fact",
        "wrong_status_key",
        "wrong_source_digest",
        "wrong_source_selector",
        "wrong_rule",
        "wrong_ai_version",
        "wrong_ai_scf",
        "wrong_destination",
    ],
)
def test_carrier_shape_negative_vectors(fault: str) -> None:
    value = carrier(rows()[0])
    if fault == "missing_owner":
        del value["declaring_adr_id"]
    elif fault == "bad_uuid":
        value["declaring_adr_id"] = "not-a-uuid"
    elif fault == "duplicate_value":
        value["lifecycle_stage"] = "accepted"
    elif fault == "unknown_fact":
        value["proof"] = True
    elif fault == "wrong_status_key":
        value["status_semantic_field_key"] = "adr/physical-system#/status"
    elif fault == "wrong_source_digest":
        value["status_source_authority"]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "wrong_source_selector":
        value["status_source_authority"]["schema_pointer"] = "/properties/title"
    elif fault == "wrong_rule":
        value["ownership_rule"]["rule_id"] = "unknown-rule"
    elif fault == "wrong_ai_version":
        value["ownership_rule"]["version"] = "1.2"
    elif fault == "wrong_ai_scf":
        value["ownership_rule"]["semantic_contract_fingerprint"] = "invalid"
    else:
        value["value_destination"] = "/metadata/status"
    assert not Draft202012Validator(
        read(CANONICAL / "resources/lifecycle-provenance.schema.json")
    ).is_valid(value)


def test_schema_valid_carrier_is_not_runtime_ownership_or_digest_proof() -> None:
    value = carrier(rows()[0])
    value["declaring_adr_id"] = "019109a0-b1c2-7def-8a00-112233445567"
    value["ownership_rule"]["content_digest"] = "sha256:" + "0" * 64
    # Shape alone cannot establish the owner or a well-formed but false digest.
    assert Draft202012Validator(
        read(CANONICAL / "resources/lifecycle-provenance.schema.json")
    ).is_valid(value)
    fact = read(CANONICAL / "resources/contextual-facts.json")["facts"][0]
    assert fact["carrier_assertions_alone"] == "insufficient_proof_of_ownership_or_lifecycle"
    assert "declaring_adr_id" in fact["semantic_equality_fields"]
    assert "ownership_rule.rule_id" in fact["semantic_equality_fields"]
    assert (
        fact["first_class_value"]
        == "compared_once_as_complete_literal_lifecycle_value_not_copied_into_carrier"
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing_row",
        "duplicate_row",
        "wrong_parent",
        "reference_path",
        "wrong_digest",
        "wrong_status",
        "wrong_destination",
        "missing_fact",
        "extra_fact",
        "wrong_context_identity",
        "nonliteral_status",
        "root_source_authority",
        "root_output_authority",
        "stale_extension_carrier",
        "stale_extension_authority",
        "stale_context_qualification",
        "changed_disposition",
        "unknown_destination",
        "missing_carrier_property",
        "additional_carrier_property",
        "self_scf",
        "broken_schema_ref",
    ],
)
def test_publication_faults_prevent_qualification(candidate: Path, fault: str) -> None:
    base = candidate / "contracts/architecture-interpretation/v1.3/resources"
    name = "lifecycle-ownership"
    value = read(base / (name + ".json"))
    if fault == "missing_row":
        value["rows"].pop()
    elif fault == "duplicate_row":
        value["rows"][-1] = value["rows"][0]
    elif fault == "wrong_parent":
        value["rows"][0]["parent_semantic_type"] = "entity/component"
    elif fault == "reference_path":
        value["rows"][0]["source_instance_pattern"] = "/related_adrs/*"
    elif fault == "wrong_digest":
        value["rows"][0]["source_schema"]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "wrong_status":
        value["rows"][0]["status_semantic_field_key"] = "adr/logical#/title"
    elif fault == "wrong_destination":
        value["destination_schema"]["schema_pointer"] = "/oneOf/1"
    elif fault in {"stale_extension_carrier", "stale_extension_authority"}:
        name = "rules"
        value = read(base / (name + ".json"))
        field = "carrier" if fault == "stale_extension_carrier" else "meaning_authority"
        value["semantic_extensions"][field]["contract_version"] = (
            "2.4" if field == "carrier" else "1.2"
        )
    elif fault == "stale_context_qualification":
        name = "detached-context"
        value = read(base / (name + ".json"))
        value["derivation"][
            "contract_identity"
        ] = "exact AI 1.2 and NM 2.4 identities participate in context qualification but not locator derivation"
    elif fault in {"missing_fact", "extra_fact", "wrong_context_identity"}:
        name = "contextual-facts"
        value = read(base / (name + ".json"))
        if fault == "missing_fact":
            value["facts"] = []
        elif fault == "extra_fact":
            value["facts"].append(value["facts"][0])
        else:
            value["facts"][0]["semantic_identity"] = "source_pointer"
    elif fault in {"nonliteral_status", "root_source_authority", "root_output_authority"}:
        name = "rules"
        value = read(base / (name + ".json"))
        authority = value["lifecycle_authority"]
        if fault == "nonliteral_status":
            authority["authored_to_normalized"]["accepted"] = "active"
        elif fault == "root_source_authority":
            authority["source_status_schema"]["schema_pointer"] = "/definitions/title"
        else:
            authority["output_qualification"]["semantic_contract_fingerprint"] = (
                "scf:v1:sha256:" + "0" * 64
            )
    elif fault in {"changed_disposition", "unknown_destination"}:
        name = "field-dispositions-1.7-to-2.5"
        value = read(base / (name + ".json"))
        field = value["semantic_types"][0]["field_dispositions"][0]
        field["destination_ref" if fault == "unknown_destination" else "disposition"] = "unknown"
    else:
        name = "lifecycle-provenance.schema"
        value = read(base / (name + ".json"))
        if fault == "missing_carrier_property":
            value["required"].pop()
        elif fault == "additional_carrier_property":
            value["properties"]["lifecycle_stage"] = {"type": "string"}
        elif fault == "self_scf":
            value["properties"]["ownership_rule"]["properties"]["semantic_contract_fingerprint"] = {
                "const": EXPECTED_SCF
            }
        else:
            value["properties"]["declaring_adr_id"] = {"$ref": "missing.schema.json"}
    write(base / (name + ".json"), value)
    with pytest.raises(publication.PublicationError):
        publication.qualify_publication(candidate)


def test_selector_and_source_object_permutations_preserve_publication_proof(
    candidate: Path,
) -> None:
    baseline = publication.qualify_publication(candidate)
    path = (
        candidate / "contracts/architecture-interpretation/v1.3/resources/lifecycle-ownership.json"
    )
    value = read(path)
    value["rows"].reverse()
    write(path, value)
    source = candidate / "schema/authoring/v1.7/adr-logical.schema.json"
    value = read(source)
    value["properties"] = dict(reversed(list(value["properties"].items())))
    write(source, value)
    assert publication.qualify_publication(candidate) == baseline


@pytest.mark.parametrize(
    "fault",
    [
        "missing_ref",
        "escaping_ref",
        "conflicting_allof",
        "conditional_branch",
        "conditional_reference",
        "unbounded_union",
        "unsupported_keyword",
        "missing_target_value",
        "ambiguous_target",
    ],
)
def test_complete_enum_domain_proof_fails_closed(fault: str) -> None:
    documents = publication.source_documents(ROOT)
    source = documents["adr-logical.schema.json"]
    destination = read(ROOT / "schema/normalized-model/v2.5/normalized-entity.schema.json")
    if fault == "missing_ref":
        source["properties"]["status"] = {"$ref": "missing.schema.json"}
    elif fault == "escaping_ref":
        source["properties"]["status"] = {"$ref": "../../../ambient/status.json"}
    elif fault == "conflicting_allof":
        source["allOf"] = [{"properties": {"status": {"enum": ["active"]}}}]
    elif fault == "conditional_branch":
        source["anyOf"] = [{"properties": {"status": {"enum": ["accepted"]}}}]
    elif fault == "conditional_reference":
        source["if"] = {"$ref": "missing-conditional.schema.json"}
    elif fault == "unbounded_union":
        source["properties"]["status"] = {"anyOf": [{"enum": ["proposed"]}, {"type": "string"}]}
    elif fault == "unsupported_keyword":
        source["properties"]["status"] = {"enum": ["accepted"], "x-conversion": "active"}
    elif fault == "missing_target_value":
        destination["oneOf"][0]["properties"]["lifecycle_stage"]["enum"].remove("accepted")
    else:
        destination["oneOf"].append(copy.deepcopy(destination["oneOf"][0]))
    with pytest.raises(publication.PublicationError):
        publication.prove_enum_inclusion(source, destination, [*documents.values(), destination])


def test_historical_contradiction_is_diagnostic_not_retroactive_conformance() -> None:
    documents = publication.source_documents(ROOT)
    destination = read(ROOT / "schema/normalized-model/v2.4/normalized-entity.schema.json")
    for kind in publication.ROOT_TYPES:
        with pytest.raises(
            publication.PublicationError, match="source_value_outside_destination_domain"
        ):
            publication.prove_enum_inclusion(
                documents[f"adr-{kind}.schema.json"],
                destination,
                [*documents.values(), destination],
            )
    old = get_semantic_contract("architecture-interpretation", "1.2")
    assert verify_semantic_contract(old).success
    assert (
        old.semantic_contract_fingerprint
        == "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a"
    )
    bundle = [
        {
            "canonicalResourceKey": e.canonical_resource_key,
            "content": load_semantic_resource(e.canonical_resource_key),
        }
        for e in old.resource_manifest
    ]
    assert validate_semantic_resource_closure(old, bundle).closure_valid
    assert len(load_semantic_resource("architecture-interpretation/1.2/conformance")["cases"]) == 21


def test_all_frozen_cases_remain_authority_only() -> None:
    conformance = read(CANONICAL / "resources/conformance.json")
    cases = conformance["cases"]
    assert len(cases) == 137
    assert [case["id"] for case in cases] == [f"AI13-{i:03d}" for i in range(1, 138)]
    assert conformance["frozen_conformance_schema"]["authority_only"] is True
    assert conformance["frozen_conformance_schema"]["not_acc_execution"] is True
    assert Counter(case["category"] for case in cases) == {
        "inherited-requalified": 21,
        "root-lifecycle": 12,
        "schema-ownership": 68,
        "successor-authority": 36,
    }
    assert {case["rule_id"] for case in cases if "rule_id" in case} == {
        row["rule_id"] for row in rows()
    }


def test_exact_discovery_and_byte_identical_package_mirrors() -> None:
    definition = (CANONICAL / "contract.json").read_bytes()
    for path in (
        ASSETS / "definitions/architecture-interpretation-1.3.json",
        BUNDLED / "definitions/architecture-interpretation-1.3.json",
        BUNDLED / "architecture-interpretation-1.3.json",
    ):
        assert path.read_bytes() == definition
    for name in publication.RESOURCE_NAMES:
        data = (CANONICAL / "resources" / (name + ".json")).read_bytes()
        filename = "architecture-interpretation-1.3-" + name + ".json"
        assert (ASSETS / "resources" / filename).read_bytes() == data
        assert (BUNDLED / "resources" / filename).read_bytes() == data
        assert EXPECTED_SCF not in data.decode("utf-8")
    assert all(x.semantic_contract_version != "1.3" for x in list_semantic_contracts())
    with pytest.raises(LookupError):
        get_semantic_contract("architecture-interpretation", "99.99")
    with pytest.raises(LookupError):
        load_semantic_resource("architecture-interpretation/99.99/rules")
    with pytest.raises(LookupError):
        load_semantic_resource("architecture-interpretation/1.3/not-published")
    with pytest.raises(LookupError):
        load_semantic_resource("architecture-interpretation/1.3/source-decoding-1.5")
    with pytest.raises(LookupError):
        load_semantic_resource("architecture-interpretation/1.3/lifecycle/ownership")
    with pytest.raises(LookupError):
        get_semantic_contract("authoring-construction", "1.4")


def test_successor_only_generation_deterministic_and_historical_bytes_unchanged() -> None:
    paths = [
        CANONICAL / "contract.json",
        ASSETS / "definitions/architecture-interpretation-1.3.json",
        BUNDLED / "definitions/architecture-interpretation-1.3.json",
        BUNDLED / "architecture-interpretation-1.3.json",
    ]
    paths.extend(
        directory / ("architecture-interpretation-1.3-" + name + ".json")
        for directory in (ASSETS / "resources", BUNDLED / "resources")
        for name in publication.RESOURCE_NAMES
    )
    before = {path: path.read_bytes() for path in paths}
    for _ in range(2):
        subprocess.run(
            [sys.executable, "scripts/generate_semantic_contract_assets.py", "--publish-ai13-only"],
            cwd=ROOT,
            check=True,
        )
        assert {path: path.read_bytes() for path in paths} == before
    for relative, expected in HISTORICAL_SHA256.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
