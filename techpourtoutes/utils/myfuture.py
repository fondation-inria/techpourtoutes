from django.conf import settings

from techpourtoutes.models import JobPosting

MYFUTURE_SAMPLE_PATH = settings.BASE_DIR / "data" / "myfuture" / "job_postings_sample.json"

# The sub-domains whose offers we import, keyed as MyFuture spells them: the parent domain's key
# glued to the sub-domain's own slug.
SUB_DOMAINS = {
    "electricite-electronique-robotiqueelectronique": JobPosting.Domain.ELECTRONIQUE,
    "electricite-electronique-robotiqueelectrotechnique": JobPosting.Domain.ELECTROTECHNIQUE,
    "electricite-electronique-robotiquetelecommunications": JobPosting.Domain.TELECOMMUNICATIONS,
    "informatique-internetbases-de-donnees": JobPosting.Domain.BASES_DE_DONNEES,
    "informatique-internetdeveloppement-programmation-logiciel": (JobPosting.Domain.DEVELOPPEMENT),
    "informatique-internetinformatique-de-gestion": JobPosting.Domain.INFORMATIQUE_DE_GESTION,
    "informatique-internetinformatique-generalites": JobPosting.Domain.INFORMATIQUE,
    "informatique-internetinformatique-industrielle-et-technologique": (
        JobPosting.Domain.INFORMATIQUE_INDUSTRIELLE
    ),
    "informatique-internetinformatique-pour-la-recherche": (
        JobPosting.Domain.INFORMATIQUE_POUR_LA_RECHERCHE
    ),
    "informatique-internetsystemes-et-reseaux": JobPosting.Domain.SYSTEMES_ET_RESEAUX,
    "sciencesmathematiques": JobPosting.Domain.MATHEMATIQUES,
    "sciencessciences-de-lunivers": JobPosting.Domain.SCIENCES_DE_L_UNIVERS,
}
