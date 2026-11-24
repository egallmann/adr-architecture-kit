//! Closed expectations, never proof of authority. Each use must verify closure.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Profile {
    Acc12,
    Acc13,
}

pub(crate) struct Expected {
    pub acc_version: &'static str,
    pub acc_scf: &'static str,
    pub ai_version: &'static str,
    pub ai_scf: &'static str,
    pub nm_version: &'static str,
    pub nm_scf: &'static str,
    pub schema: &'static str,
    pub rules: &'static str,
    pub table: &'static str,
    pub table_schema: &'static str,
    pub ai_contract: &'static str,
    pub dispositions: &'static str,
    pub context: &'static str,
    pub interpretation: &'static str,
}

impl Profile {
    pub(crate) fn expected(self) -> Expected {
        match self {
            Self::Acc12 => Expected {
                acc_version: "1.2",
                acc_scf:
                    "scf:v1:sha256:8da499420e996c446cbc416dc7db9b4bbb2692ea5039f14461f668aaa48b9e0c",
                ai_version: "1.2",
                ai_scf:
                    "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a",
                nm_version: "2.4",
                nm_scf:
                    "scf:v1:sha256:83f1c50cd5c63f027b1b4d937604a255d78c868629085dfd3240f2517d64d394",
                schema: "authoring-construction/1.2/schema",
                rules: "authoring-construction/1.2/rules",
                table: "authoring-construction/1.2/composition-bindings",
                table_schema: "authoring-construction/1.2/composition-bindings.schema",
                ai_contract: "architecture-interpretation/1.2/contract",
                dispositions: "architecture-interpretation/1.2/field-dispositions-1.7-to-2.4",
                context: "architecture-interpretation/1.2/detached-context",
                interpretation: "complete_nm_2_4_interpretation",
            },
            Self::Acc13 => Expected {
                acc_version: "1.3",
                acc_scf:
                    "scf:v1:sha256:5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49",
                ai_version: "1.3",
                ai_scf:
                    "scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167",
                nm_version: "2.5",
                nm_scf:
                    "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7",
                schema: "authoring-construction/1.3/schema",
                rules: "authoring-construction/1.3/rules",
                table: "authoring-construction/1.3/composition-bindings",
                table_schema: "authoring-construction/1.3/composition-bindings.schema",
                ai_contract: "architecture-interpretation/1.3/contract",
                dispositions: "architecture-interpretation/1.3/field-dispositions-1.7-to-2.5",
                context: "architecture-interpretation/1.3/detached-context",
                interpretation: "complete_nm_2_5_interpretation",
            },
        }
    }
}
