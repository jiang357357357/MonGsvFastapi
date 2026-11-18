"""Epoch metrics are independent of step logging and checkpoint frequency."""


class EpochLoss:
    def __init__(self):
        self.total = None
        self.batches = 0

    def add(self, loss):
        value = loss.detach().float()
        self.total = value if self.total is None else self.total + value
        self.batches += 1

    def write(self, writer, logger, epoch, step):
        if not self.batches:
            return
        mean = (self.total / self.batches).item()
        writer.add_scalar("loss/g/total_epoch", mean, epoch)
        writer.add_scalar("epoch", epoch, step)
        writer.flush()
        logger.info("Epoch Loss: epoch=%s step=%s mean=%.8f batches=%s", epoch, step, mean, self.batches)
