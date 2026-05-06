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


export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
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
      </Routes>
      <Footer />
    </BrowserRouter>
  );
}