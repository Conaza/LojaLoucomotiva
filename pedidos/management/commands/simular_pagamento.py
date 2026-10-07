from django.core.management.base import BaseCommand, CommandError

from pedidos.models import Pedido


class Command(BaseCommand):
    help = 'Marca como pago o pagamento mais recente de um pedido (uso em desenvolvimento).'

    def add_arguments(self, parser):
        parser.add_argument('pedido_id', type=int)

    def handle(self, *args, pedido_id, **options):
        pedido = Pedido.objects.filter(pk=pedido_id).first()
        if pedido is None:
            raise CommandError(f'Pedido {pedido_id} não encontrado.')
        pagamento = pedido.pagamento_atual
        if pagamento is None:
            raise CommandError(f'Pedido {pedido_id} não possui pagamento.')
        if not pagamento.marcar_pago():
            self.stdout.write(f'Pagamento {pagamento.order_nsu} já estava pago.')
            return
        self.stdout.write(self.style.SUCCESS(f'Pagamento {pagamento.order_nsu} marcado como pago.'))
