from django.core.management.base import BaseCommand

from rag.hybrid_retriever import get_hybrid_retriever


class Command(BaseCommand):
    help = "Build hybrid catalog index (TF-IDF + embeddings) for chatbot retrieval"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force rebuild even if index exists",
        )

    def handle(self, *args, **options):
        retriever = get_hybrid_retriever()
        force = bool(options["force"])

        if not force:
            retriever.ensure_index()
            remote = retriever._fetch_all_products()
            if remote and len(remote) == len(retriever.catalog):
                self.stdout.write(self.style.SUCCESS(
                    f"Catalog index up to date ({len(remote)} products), skip rebuild."
                ))
                return

        ok = retriever.rebuild_index(force=True)
        if ok:
            self.stdout.write(self.style.SUCCESS("Catalog hybrid index built successfully."))
        else:
            self.stdout.write(self.style.WARNING("Catalog index build skipped or failed."))
