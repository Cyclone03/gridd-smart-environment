import { Module } from '@nestjs/common';
import { ObservationsModule } from '../observations/observations.module';
import { KAFKA_CONSUMER_FACTORY, kafkaConsumerFactory } from './kafka.consumer.factory';
import { KafkaConsumerService } from './kafka.consumer.service';

@Module({
  imports: [ObservationsModule],
  providers: [
    KafkaConsumerService,
    { provide: KAFKA_CONSUMER_FACTORY, useValue: kafkaConsumerFactory },
  ],
  exports: [KafkaConsumerService],
})
export class KafkaModule {}
