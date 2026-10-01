import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Observation } from './entities/observation.entity';
import { ObservationInput } from './interfaces/observation-input.interface';

@Injectable()
export class ObservationService {
  constructor(
    @InjectRepository(Observation)
    private readonly observationsRepository: Repository<Observation>,
  ) {}

  create(input: ObservationInput): Promise<Observation> {
    const observation = this.observationsRepository.create(input);
    return this.observationsRepository.save(observation);
  }

  findAll(): Promise<Observation[]> {
    return this.observationsRepository.find({
      order: { receivedAt: 'DESC' },
    });
  }

  findLatest(): Promise<Observation[]> {
    return this.observationsRepository
      .createQueryBuilder('observation')
      .distinctOn(['observation.type'])
      .orderBy('observation.type', 'ASC')
      .addOrderBy(
        'COALESCE(observation.observedAt, observation.receivedAt)',
        'DESC',
      )
      .addOrderBy('observation.receivedAt', 'DESC')
      .getMany();
  }
}
