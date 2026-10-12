import type { Card } from "../../lib/api";
import OutcomeCard from "./OutcomeCard";
import LadderCard from "./LadderCard";
import ProviderCard from "./ProviderCard";
import CostsCard from "./CostsCard";

export default function CardView({ card }: { card: Card }) {
  switch (card.type) {
    case "outcome":
      return <OutcomeCard card={card} />;
    case "ladder":
      return <LadderCard card={card} />;
    case "providers":
      return <ProviderCard card={card} />;
    case "costs":
      return <CostsCard card={card} />;
    default:
      return null;
  }
}
