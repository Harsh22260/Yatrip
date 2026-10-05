import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";

// Hotels
import HotelsListPage from "./pages/hotels/HotelsListPage";
import HotelDetailPage from "./pages/hotels/HotelDetailPage";
import MyBookingsPage from "./pages/hotels/MyBookingsPage";
import RegisterHotelPage from "./pages/hotels/RegisterHotelPage";
import MyHotelsPage from "./pages/hotels/MyHotelsPage";

// Other sections
import RentalsListPage from "./pages/rentals/RentalsListPage";
import RentalDetailPage from "./pages/rentals/RentalDetailPage";
import RegisterRentalPage from "./pages/rentals/RegisterRentalPage";
import MyRentalsPage from "./pages/rentals/MyRentalsPage";

// Food
import FoodListPage from "./pages/food/FoodListPage";
import FoodDetailPage from "./pages/food/FoodDetailPage";
import RegisterFoodPage from "./pages/food/RegisterFoodPage";
import MyFoodPlacesPage from "./pages/food/MyFoodPlacesPage";

// Attractions
import AttractionsListPage from "./pages/attractions/AttractionsListPage";
import AttractionDetailPage from "./pages/attractions/AttractionDetailPage";
import RegisterAttractionPage from "./pages/attractions/RegisterAttractionPage";
import MyAttractionsPage from "./pages/attractions/MyAttractionsPage";

import TransportPage from "./pages/transport/TransportPage";
import ChatbotPage from "./pages/chatbot/ChatbotPage";
import InfoPage from "./pages/info/InfoPage";
import NotFound from "./pages/NotFound";


export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}

/* The navbar is position:sticky, so it reserves its own height in the flow and
   every route is pushed down by exactly --nav-h. An earlier version made it
   position:fixed and had this wrapper add the same offset again, which left a
   92-320px dead band under the bar because each page also had padding of its
   own. No per-page clearance and no per-route exception is needed now. */
function Shell() {
  return (
    <>
      <Navbar />
      <main className="app-main">
        <Routes>
          <Route path="/"                   element={<Home />} />
          <Route path="/login"              element={<Login />} />
          <Route path="/register"           element={<Register />} />
          <Route path="/profile"            element={<Profile />} />

          {/* Hotels */}
          <Route path="/hotels"             element={<HotelsListPage />} />
          <Route path="/hotels/:id"         element={<HotelDetailPage />} />
          <Route path="/my-bookings"        element={<MyBookingsPage />} />

          {/* Business */}
          <Route path="/register-hotel"     element={<RegisterHotelPage />} />
          <Route path="/my-hotels"          element={<MyHotelsPage />} />
          <Route path="/register-rental"    element={<RegisterRentalPage />} />
          <Route path="/my-rentals"         element={<MyRentalsPage />} />
          <Route path="/register-food"      element={<RegisterFoodPage />} />
          <Route path="/my-food-places"     element={<MyFoodPlacesPage />} />
          <Route path="/register-attraction" element={<RegisterAttractionPage />} />
          <Route path="/my-attractions"     element={<MyAttractionsPage />} />

          {/* Others */}
          <Route path="/attractions"        element={<AttractionsListPage />} />
          <Route path="/attractions/:id"    element={<AttractionDetailPage />} />
          <Route path="/food"               element={<FoodListPage />} />
          <Route path="/food/:id"           element={<FoodDetailPage />} />
          <Route path="/transport"          element={<TransportPage />} />
          <Route path="/rentals"            element={<RentalsListPage />} />
          <Route path="/rentals/:id"        element={<RentalDetailPage />} />
          <Route path="/chatbot"            element={<ChatbotPage />} />

          {/* Static pages. The navbar and footer linked to all four, but none
              were registered, so each one rendered a blank page. */}
          <Route path="/about"              element={<InfoPage />} />
          <Route path="/contact"            element={<InfoPage />} />
          <Route path="/privacy"            element={<InfoPage />} />
          <Route path="/terms"              element={<InfoPage />} />

          {/* Anything unrecognised. Without this React rendered no route at all
              between the navbar and footer, which read as a broken page. */}
          <Route path="*"                   element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </>
  );
}